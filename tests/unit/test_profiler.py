"""Unit tests for automated CSV dataset profiling logic."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.services.profiler import profile_csv_file


def test_profile_csv_basic_numeric_and_string() -> None:
    csv_content = """name,age,salary,is_active,signup_date
Alice,30,75000.50,true,2026-01-15
Bob,25,50000.00,false,2026-02-20
Charlie,35,100000.00,true,2026-03-10
David,NA,null,true,2026-04-05
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        f_path = Path(f.name)

    try:
        row_count, col_count, columns = profile_csv_file(f_path)
        assert row_count == 4
        assert col_count == 5

        col_dict = {col["name"]: col for col in columns}

        # Check name (string)
        assert col_dict["name"]["inferred_type"] == "string"
        assert col_dict["name"]["missing_count"] == 0
        assert col_dict["name"]["unique_count"] == 4

        # Check age (integer with 1 missing 'NA')
        assert col_dict["age"]["inferred_type"] == "integer"
        assert col_dict["age"]["missing_count"] == 1
        assert col_dict["age"]["missing_percentage"] == 25.0
        assert col_dict["age"]["min_value"] == 25
        assert col_dict["age"]["max_value"] == 35
        assert col_dict["age"]["mean_value"] == 30.0

        # Check salary (float with 1 missing 'null')
        assert col_dict["salary"]["inferred_type"] == "float"
        assert col_dict["salary"]["missing_count"] == 1
        assert col_dict["salary"]["missing_percentage"] == 25.0
        assert col_dict["salary"]["min_value"] == 50000.0
        assert col_dict["salary"]["max_value"] == 100000.0
        assert round(col_dict["salary"]["mean_value"], 2) == 75000.17

        # Check is_active (boolean)
        assert col_dict["is_active"]["inferred_type"] == "boolean"
        assert col_dict["is_active"]["missing_count"] == 0

        # Check signup_date (datetime)
        assert col_dict["signup_date"]["inferred_type"] == "datetime"
        assert col_dict["signup_date"]["missing_count"] == 0

    finally:
        if f_path.exists():
            f_path.unlink()


def test_profile_csv_empty_header_only() -> None:
    csv_content = "header1,header2,header3\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        f_path = Path(f.name)

    try:
        row_count, col_count, columns = profile_csv_file(f_path)
        assert row_count == 0
        assert col_count == 3
        assert len(columns) == 3
        assert columns[0]["missing_count"] == 0
        assert columns[0]["missing_percentage"] == 0.0
    finally:
        if f_path.exists():
            f_path.unlink()


def test_profile_csv_top_values_categorical() -> None:
    csv_content = """category
Apple
Apple
Banana
Apple
Orange
Banana
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        f_path = Path(f.name)

    try:
        row_count, col_count, columns = profile_csv_file(f_path)
        assert row_count == 6
        cat_col = columns[0]
        assert cat_col["inferred_type"] == "string"
        assert cat_col["unique_count"] == 3
        assert cat_col["top_values"] is not None
        assert cat_col["top_values"][0] == {"value": "Apple", "count": 3}
        assert cat_col["top_values"][1] == {"value": "Banana", "count": 2}
    finally:
        if f_path.exists():
            f_path.unlink()
