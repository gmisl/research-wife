"""Deterministic weekly statistics for comparable wholesale prices."""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
import sqlite3


@dataclass
class WeeklyStat:
    week_start: str
    week_end: str
    country_code: str | None
    product_id: int
    product_family: str
    category_name: str
    avg_price_eur: float
    median_price_eur: float
    min_price_eur: float
    max_price_eur: float
    sample_count: int
    supplier_count: int
    previous_avg_price_eur: float | None
    change_pct: float | None
    trend_direction: str


def monday(value: date) -> date:
    return value - timedelta(days=value.weekday())


def comparable_price_rows(connection: sqlite3.Connection):
    return connection.execute(
        """
        SELECT p.price_date, s.country_code, p.product_id,
               pr.product_family, pr.category_name,
               p.price_eur, p.supplier_id
        FROM prices p
        JOIN suppliers s ON s.id = p.supplier_id
        JOIN products pr ON pr.id = p.product_id
        JOIN certifications c ON c.supplier_id = s.id AND c.status = 'verified'
        WHERE p.price_status = 'published'
          AND p.is_wholesale = 1
          AND p.price_eur IS NOT NULL
          AND p.price_unit IN ('EUR/kg', 'EUR/tonne')
          AND s.status = 'active'
        ORDER BY p.price_date
        """
    ).fetchall()


def calculate_weekly_stats(connection: sqlite3.Connection) -> list[WeeklyStat]:
    groups: dict[tuple[str, str | None, int], list[tuple[float, int, str, str]]] = defaultdict(list)
    for row in comparable_price_rows(connection):
        price_date = date.fromisoformat(row[0])
        week = monday(price_date).isoformat()
        groups[(week, row[1], row[2])].append((float(row[5]), row[6], row[3], row[4]))

    ordered = sorted(groups)
    previous: dict[tuple[str | None, int], float] = {}
    result: list[WeeklyStat] = []
    for week, country, product_id in ordered:
        values = groups[(week, country, product_id)]
        prices = [x[0] for x in values]
        avg = sum(prices) / len(prices)
        old_avg = previous.get((country, product_id))
        change = None if old_avg in (None, 0) else ((avg - old_avg) / old_avg) * 100
        if change is None:
            direction = 'insufficient_data'
        elif change > 2:
            direction = 'up'
        elif change < -2:
            direction = 'down'
        else:
            direction = 'stable'
        result.append(WeeklyStat(
            week_start=week,
            week_end=(date.fromisoformat(week) + timedelta(days=6)).isoformat(),
            country_code=country,
            product_id=product_id,
            product_family=values[0][2],
            category_name=values[0][3],
            avg_price_eur=round(avg, 4),
            median_price_eur=round(statistics.median(prices), 4),
            min_price_eur=min(prices),
            max_price_eur=max(prices),
            sample_count=len(prices),
            supplier_count=len({x[1] for x in values}),
            previous_avg_price_eur=old_avg,
            change_pct=None if change is None else round(change, 2),
            trend_direction=direction,
        ))
        previous[(country, product_id)] = avg
    return result
