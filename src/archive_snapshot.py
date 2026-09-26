"""Append the current weekly price statistics to a committed history file."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from .stats import calculate_weekly_stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/research-wife.db")
    parser.add_argument("--output", default="data/history/weekly_price_snapshots.json")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        history = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        history = []
    if not isinstance(history, list):
        history = []

    with sqlite3.connect(args.database) as db:
        current = [asdict(row) for row in calculate_weekly_stats(db)]

    keys = {(row.get("week_start"), row.get("country_code"), row.get("product_id")) for row in history}
    history.extend(row for row in current
                   if (row.get("week_start"), row.get("country_code"), row.get("product_id")) not in keys)
    history.sort(key=lambda row: (row.get("week_start", ""), row.get("country_code") or "", row.get("product_id", 0)))
    output.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Archived {len(current)} current rows; history now has {len(history)} rows")


if __name__ == "__main__":
    main()
