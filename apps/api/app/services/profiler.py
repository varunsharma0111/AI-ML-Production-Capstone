"""Automated CSV profiling service calculating dataset and column-level statistics."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

NULL_VALUES = {"", "null", "none", "na", "n/a", "nan", "undefined"}


def _is_null(val: str) -> bool:
    return val.strip().lower() in NULL_VALUES


def _try_parse_int(val: str) -> int | None:
    try:
        s = val.strip()
        ival = int(s)
        if str(ival) == s:
            return ival
        return None
    except ValueError:
        return None


def _try_parse_float(val: str) -> float | None:
    try:
        return float(val.strip())
    except ValueError:
        return None


def _try_parse_bool(val: str) -> bool | None:
    v = val.strip().lower()
    if v in ("true", "false", "yes", "no", "t", "f"):
        return v in ("true", "yes", "t")
    return None


def _try_parse_datetime(val: str) -> datetime | None:
    v = val.strip()
    if len(v) < 8:
        return None
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            pass
    return None


def profile_csv_file(file_path: Path | str | bytes) -> tuple[int, int, list[dict[str, Any]]]:
    """Read and profile CSV file, returning (row_count, column_count, columns_data)."""

    import io

    from app.core.storage import StorageService

    file_obj: io.StringIO | io.TextIOWrapper

    if isinstance(file_path, bytes):
        file_obj = io.StringIO(file_path.decode("utf-8-sig", errors="replace"))
    else:
        path = Path(file_path)
        if path.exists() and path.is_file():
            file_obj = path.open("r", encoding="utf-8-sig", errors="replace")
        else:
            try:
                content_bytes = StorageService().read_dataset_file(str(file_path))
                file_obj = io.StringIO(content_bytes.decode("utf-8-sig", errors="replace"))
            except Exception as err:
                raise FileNotFoundError(f"CSV file not found at {file_path}") from err

    try:
        reader = csv.reader(file_obj)
        try:
            header = next(reader)
        except StopIteration:
            return 0, 0, []

        column_names = [col.strip() or f"col_{i}" for i, col in enumerate(header)]
        col_count = len(column_names)

        row_count = 0
        missing_counts = [0] * col_count
        unique_sets: list[set[str]] = [set() for _ in range(col_count)]
        val_counters: list[Counter[str]] = [Counter() for _ in range(col_count)]

        int_counts = [0] * col_count
        float_counts = [0] * col_count
        bool_counts = [0] * col_count
        dt_counts = [0] * col_count

        num_counts = [0] * col_count
        num_sums = [0.0] * col_count
        num_mins = [float("inf")] * col_count
        num_maxs = [float("-inf")] * col_count

        for row in reader:
            if not row or all(not cell.strip() for cell in row):
                continue
            row_count += 1
            for i in range(col_count):
                val = row[i] if i < len(row) else ""
                val_str = val.strip()

                if _is_null(val_str):
                    missing_counts[i] += 1
                else:
                    if len(unique_sets[i]) < 1000:
                        unique_sets[i].add(val_str)

                    if len(val_counters[i]) < 1000 or val_str in val_counters[i]:
                        val_counters[i][val_str] += 1

                    parsed_int = _try_parse_int(val_str)
                    parsed_float = _try_parse_float(val_str)
                    parsed_bool = _try_parse_bool(val_str)
                    parsed_dt = _try_parse_datetime(val_str)

                    if parsed_int is not None:
                        int_counts[i] += 1
                        fval = float(parsed_int)
                        num_counts[i] += 1
                        num_sums[i] += fval
                        if fval < num_mins[i]:
                            num_mins[i] = fval
                        if fval > num_maxs[i]:
                            num_maxs[i] = fval
                    elif parsed_float is not None:
                        float_counts[i] += 1
                        fval = parsed_float
                        num_counts[i] += 1
                        num_sums[i] += fval
                        if fval < num_mins[i]:
                            num_mins[i] = fval
                        if fval > num_maxs[i]:
                            num_maxs[i] = fval

                    if parsed_bool is not None:
                        bool_counts[i] += 1

                    if parsed_dt is not None:
                        dt_counts[i] += 1

        columns_stats: list[dict[str, Any]] = []

        for i, name in enumerate(column_names):
            col_missing = missing_counts[i]
            col_non_missing = row_count - col_missing
            missing_pct = round((col_missing / row_count * 100.0), 2) if row_count > 0 else 0.0
            uniq_cnt = len(unique_sets[i])

            inferred_type = "string"
            if col_non_missing > 0:
                if int_counts[i] == col_non_missing:
                    inferred_type = "integer"
                elif (int_counts[i] + float_counts[i]) == col_non_missing:
                    inferred_type = "float"
                elif bool_counts[i] == col_non_missing:
                    inferred_type = "boolean"
                elif dt_counts[i] == col_non_missing:
                    inferred_type = "datetime"

            col_data: dict[str, Any] = {
                "name": name,
                "inferred_type": inferred_type,
                "missing_count": col_missing,
                "missing_percentage": missing_pct,
                "unique_count": uniq_cnt,
            }

            if inferred_type in ("integer", "float") and num_counts[i] > 0:
                min_v = num_mins[i]
                max_v = num_maxs[i]
                mean_v = num_sums[i] / num_counts[i]
                if inferred_type == "integer":
                    col_data["min_value"] = int(min_v)
                    col_data["max_value"] = int(max_v)
                else:
                    col_data["min_value"] = round(min_v, 4)
                    col_data["max_value"] = round(max_v, 4)
                col_data["mean_value"] = round(mean_v, 4)
            else:
                col_data["min_value"] = None
                col_data["max_value"] = None
                col_data["mean_value"] = None

            if inferred_type not in ("integer", "float") or uniq_cnt <= 20:
                top_items = val_counters[i].most_common(5)
                col_data["top_values"] = [
                    {"value": item[0], "count": item[1]} for item in top_items
                ]
            else:
                col_data["top_values"] = None

            columns_stats.append(col_data)

    finally:
        file_obj.close()

    return row_count, col_count, columns_stats
