"""Create an empty Research Wife v2 database from the versioned schema."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/research-wife.db")
    parser.add_argument("--schema", default="schema.sql")
    args = parser.parse_args()

    database = Path(args.database)
    database.parent.mkdir(parents=True, exist_ok=True)
    schema = Path(args.schema).read_text(encoding="utf-8")

    with sqlite3.connect(database) as connection:
        connection.executescript(schema)
        tables = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]

    print(f"Initialised {database} with {tables} tables")


if __name__ == "__main__":
    main()
