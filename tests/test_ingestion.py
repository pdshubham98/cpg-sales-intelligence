"""
Unit tests for data ingestion + quality rules.
"""
import os
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest


def _write_csv(tmp_path: Path, filename: str, content: str) -> Path:
    path = tmp_path / filename
    path.write_text(textwrap.dedent(content).strip())
    return path


def _make_data_dir(tmp_path: Path) -> Path:
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)

    (raw_dir / "regions.csv").write_text(
        "region_id,region_name,country,sales_manager\nR001,North America,USA,Alice\n"
    )
    (raw_dir / "products.csv").write_text(
        "product_id,sku,product_name,category,unit_price\nP001,BEV-001,Water,Beverages,1.99\n"
    )
    return raw_dir


@pytest.fixture()
def patched_env(tmp_path):
    db_file = tmp_path / "test.db"
    raw_dir = _make_data_dir(tmp_path)
    env = {"DB_PATH": str(db_file)}
    with patch.dict(os.environ, env), patch(
        "src.ingestion.loader.DATA_DIR", raw_dir
    ):
        yield tmp_path, raw_dir


def _write_sales(raw_dir: Path, rows: str) -> None:
    header = (
        "transaction_id,date,region_id,product_id,sku,"
        "quantity,unit_price,discount_pct,channel\n"
    )
    (raw_dir / "sales_transactions.csv").write_text(header + rows)


class TestDuplicateRemoval:
    def test_duplicate_transaction_ids_are_dropped(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(
            raw_dir,
            "T001,2024-01-01,R001,P001,BEV-001,10,1.99,0.0,Retail\n"
            "T001,2024-01-02,R001,P001,BEV-001,20,1.99,0.0,Retail\n",
        )
        from src.ingestion.loader import run_ingestion
        result = run_ingestion()
        assert result["raw_rows"] == 2
        assert result["clean_rows"] == 1
        assert "duplicate transaction_id" in result["quality_issues"]

    def test_unique_transactions_are_kept(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(
            raw_dir,
            "T001,2024-01-01,R001,P001,BEV-001,10,1.99,0.0,Retail\n"
            "T002,2024-01-02,R001,P001,BEV-001,20,1.99,0.0,Retail\n",
        )
        from src.ingestion.loader import run_ingestion
        result = run_ingestion()
        assert result["clean_rows"] == 2


class TestNullHandling:
    def test_null_region_id_dropped(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(
            raw_dir,
            "T001,2024-01-01,,P001,BEV-001,10,1.99,0.0,Retail\n",
        )
        from src.ingestion.loader import run_ingestion
        result = run_ingestion()
        assert result["clean_rows"] == 0
        assert "null or empty region_id" in result["quality_issues"]

    def test_null_product_id_dropped(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(
            raw_dir,
            "T001,2024-01-01,R001,,BEV-001,10,1.99,0.0,Retail\n",
        )
        from src.ingestion.loader import run_ingestion
        result = run_ingestion()
        assert result["clean_rows"] == 0

    def test_null_quantity_dropped(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(
            raw_dir,
            "T001,2024-01-01,R001,P001,BEV-001,,1.99,0.0,Retail\n",
        )
        from src.ingestion.loader import run_ingestion
        result = run_ingestion()
        assert result["clean_rows"] == 0

    def test_null_unit_price_dropped(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(
            raw_dir,
            "T001,2024-01-01,R001,P001,BEV-001,10,,0.0,Retail\n",
        )
        from src.ingestion.loader import run_ingestion
        result = run_ingestion()
        assert result["clean_rows"] == 0


class TestDateNormalization:
    def test_mm_dd_yyyy_accepted(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(
            raw_dir,
            "T001,01/15/2024,R001,P001,BEV-001,10,1.99,0.0,Retail\n",
        )
        from src.ingestion.loader import run_ingestion
        result = run_ingestion()
        assert result["clean_rows"] == 1

    def test_bad_date_dropped(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(
            raw_dir,
            "T001,not-a-date,R001,P001,BEV-001,10,1.99,0.0,Retail\n",
        )
        from src.ingestion.loader import run_ingestion
        result = run_ingestion()
        assert result["clean_rows"] == 0
        assert "unparseable date" in result["quality_issues"]


class TestSkuNormalization:
    def test_lowercase_sku_is_uppercased(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(
            raw_dir,
            "T001,2024-01-01,R001,P001,bev-001,10,1.99,0.0,Retail\n",
        )
        from src.ingestion.loader import run_ingestion
        from src.ingestion.schema import get_connection
        result = run_ingestion()
        assert result["clean_rows"] == 1
        with get_connection() as conn:
            row = conn.execute(
                "SELECT sku FROM sales_transactions WHERE transaction_id='T001'"
            ).fetchone()
        assert row["sku"] == "BEV-001"


class TestRevenueDerivation:
    def test_revenue_calculated_correctly(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(
            raw_dir,
            "T001,2024-01-01,R001,P001,BEV-001,100,2.00,0.10,Retail\n",
        )
        from src.ingestion.loader import run_ingestion
        from src.ingestion.schema import get_connection
        run_ingestion()
        with get_connection() as conn:
            row = conn.execute(
                "SELECT revenue FROM sales_transactions WHERE transaction_id='T001'"
            ).fetchone()
        # 100 * 2.00 * (1 - 0.10) = 180.00
        assert row["revenue"] == pytest.approx(180.00, rel=1e-4)


class TestMultiSourceIngestion:
    def _write_ecommerce(self, raw_dir: Path, rows: str) -> None:
        header = (
            "order_id,order_date,region_code,product_code,sku_ref,"
            "qty,unit_price_eur,promo_pct,channel,currency,customer_segment\n"
        )
        (raw_dir / "sales_ecommerce.csv").write_text(header + rows)

    def test_both_sources_merged(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(raw_dir, "T001,2024-01-01,R001,P001,BEV-001,10,1.99,0.0,Retail\n")
        self._write_ecommerce(
            raw_dir,
            "WEB001,01/15/2024,R001,P001,BEV-001,5,1.83,0.0,E-Commerce,EUR,standard\n",
        )
        from src.ingestion.loader import run_ingestion
        result = run_ingestion()
        assert result["clean_rows"] == 2
        assert result["sources"]["POS"]["clean"] == 1
        assert result["sources"]["E-Commerce"]["clean"] == 1

    def test_ecommerce_currency_converted(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(raw_dir, "")
        self._write_ecommerce(
            raw_dir,
            "WEB001,01/15/2024,R001,P001,BEV-001,10,2.00,0.0,E-Commerce,EUR,standard\n",
        )
        from src.ingestion.loader import run_ingestion, _EUR_TO_USD
        from src.ingestion.schema import get_connection
        result = run_ingestion()
        assert result["currency_conversions"] == 1
        with get_connection() as conn:
            row = conn.execute(
                "SELECT unit_price FROM sales_transactions WHERE transaction_id='WEB001'"
            ).fetchone()
        assert row["unit_price"] == pytest.approx(2.00 * _EUR_TO_USD, rel=1e-4)

    def test_ecommerce_date_format_normalised(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(raw_dir, "")
        self._write_ecommerce(
            raw_dir,
            "WEB001,03/15/2024,R001,P001,BEV-001,10,1.83,0.0,E-Commerce,EUR,standard\n",
        )
        from src.ingestion.loader import run_ingestion
        from src.ingestion.schema import get_connection
        run_ingestion()
        with get_connection() as conn:
            row = conn.execute(
                "SELECT date FROM sales_transactions WHERE transaction_id='WEB001'"
            ).fetchone()
        assert row["date"] == "2024-03-15"

    def test_cross_source_deduplication(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(raw_dir, "T001,2024-01-01,R001,P001,BEV-001,10,1.99,0.0,Retail\n")
        self._write_ecommerce(
            raw_dir,
            "T001,01/01/2024,R001,P001,BEV-001,10,1.83,0.0,E-Commerce,EUR,standard\n",
        )
        from src.ingestion.loader import run_ingestion
        result = run_ingestion()
        assert result["clean_rows"] == 1
        assert "duplicate transaction_id" in result["quality_issues"]

    def test_late_arriving_rows_detected(self, patched_env):
        tmp_path, raw_dir = patched_env
        # Most recent record is Dec 2024; include one from Jan 2024 (late-arriving)
        _write_sales(
            raw_dir,
            "T001,2024-12-01,R001,P001,BEV-001,10,1.99,0.0,Retail\n"
            "T002,2024-01-01,R001,P001,BEV-001,5,1.99,0.0,Retail\n",
        )
        from src.ingestion.loader import run_ingestion
        result = run_ingestion()
        assert result["late_arriving_rows"] >= 1

    def test_missing_ecommerce_source_is_skipped(self, patched_env):
        tmp_path, raw_dir = patched_env
        _write_sales(raw_dir, "T001,2024-01-01,R001,P001,BEV-001,10,1.99,0.0,Retail\n")
        # No ecommerce file — should not raise
        from src.ingestion.loader import run_ingestion
        result = run_ingestion()
        assert result["clean_rows"] == 1


class TestIncrementalIngestion:
    def test_upsert_is_idempotent(self, patched_env):
        """Running ingestion twice with the same data must not duplicate rows."""
        tmp_path, raw_dir = patched_env
        _write_sales(raw_dir, "T001,2024-01-01,R001,P001,BEV-001,10,1.99,0.0,Retail\n")
        from src.ingestion.loader import run_ingestion
        from src.ingestion.schema import get_connection
        run_ingestion()
        run_ingestion()
        with get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM sales_transactions WHERE transaction_id='T001'"
            ).fetchone()[0]
        assert count == 1

    def test_new_records_appended_on_second_run(self, patched_env):
        """Second ingestion with an extra row should add it without removing existing."""
        tmp_path, raw_dir = patched_env
        _write_sales(raw_dir, "T001,2024-01-01,R001,P001,BEV-001,10,1.99,0.0,Retail\n")
        from src.ingestion.loader import run_ingestion
        from src.ingestion.schema import get_connection
        run_ingestion()
        _write_sales(
            raw_dir,
            "T001,2024-01-01,R001,P001,BEV-001,10,1.99,0.0,Retail\n"
            "T002,2024-02-01,R001,P001,BEV-001,20,1.99,0.0,Retail\n",
        )
        run_ingestion()
        with get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM sales_transactions"
            ).fetchone()[0]
        assert count == 2

    def test_ingestion_log_records_run(self, patched_env):
        """Each run must write one row to ingestion_log."""
        tmp_path, raw_dir = patched_env
        _write_sales(raw_dir, "T001,2024-01-01,R001,P001,BEV-001,10,1.99,0.0,Retail\n")
        from src.ingestion.loader import run_ingestion
        from src.ingestion.schema import get_connection
        run_ingestion()
        with get_connection() as conn:
            rows = conn.execute("SELECT raw_rows, clean_rows FROM ingestion_log").fetchall()
        assert len(rows) >= 1
        assert rows[-1]["raw_rows"] >= 1
        assert rows[-1]["clean_rows"] >= 1
