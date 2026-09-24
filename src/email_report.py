"""Build a concise HTML email from the latest dashboard statistics."""

from __future__ import annotations

import argparse
import sqlite3
from html import escape
from pathlib import Path
from collections import defaultdict

from .stats import calculate_weekly_stats
from .report import load_candidate_price_signals


def build_email(connection: sqlite3.Connection, candidate_path: Path = Path('data/initial_candidates.json')) -> str:
    stats = calculate_weekly_stats(connection)
    candidate_prices = load_candidate_price_signals(candidate_path)
    suppliers = connection.execute("SELECT COUNT(*) FROM suppliers WHERE status <> 'rejected'").fetchone()[0]
    verified_suppliers = connection.execute("SELECT COUNT(*) FROM suppliers WHERE status = 'active'").fetchone()[0]
    unverified_leads = connection.execute("SELECT COUNT(*) FROM suppliers WHERE status = 'unverified'").fetchone()[0]
    new_suppliers = connection.execute("SELECT COUNT(*) FROM suppliers WHERE status = 'new'").fetchone()[0]
    lines = []
    for row in stats[-10:]:
        change = '—' if row.change_pct is None else f'{row.change_pct:+.1f}%'
        country = row.country_code or 'EU'
        lines.append(f'<tr><td>{escape(row.week_start)}</td><td>{escape(country)}</td><td>{escape(row.category_name)}</td><td>€{row.avg_price_eur:.2f}</td><td>{change}</td><td>{row.sample_count}</td></tr>')
    table = ''.join(lines) or '<tr><td colspan="6">No comparable wholesale prices collected yet.</td></tr>'
    lead_price_table = ''.join(
        f'<tr><td>{escape(row["date"])}</td><td>{escape(row["country_code"])}</td>'
        f'<td>{escape(row["legal_name"])}</td><td>{escape(row["description"])}</td>'
        f'<td>€{row["price"]:.2f} {escape(row["unit"])}</td></tr>'
        for row in candidate_prices
    ) or '<tr><td colspan="5">No published candidate price signals.</td></tr>'
    weeks = sorted({row.week_start for row in stats})
    series = defaultdict(list)
    for row in stats:
        series[row.category_name].append((row.week_start, row.avg_price_eur))
    colors = ['#2563eb', '#dc2626', '#059669', '#9333ea']
    points = []
    if weeks:
        all_values = [v for values in series.values() for _, v in values]
        low, high = min(all_values), max(all_values)
        span = max(high - low, 0.01)
        for index, (name, values) in enumerate(sorted(series.items())):
            lookup = dict(values)
            coords = []
            for i, week in enumerate(weeks):
                if week in lookup:
                    x = 40 + (i * 500 / max(len(weeks) - 1, 1))
                    y = 170 - ((lookup[week] - low) / span * 130)
                    coords.append(f'{x:.1f},{y:.1f}')
            points.append(f'<polyline fill="none" stroke="{colors[index % len(colors)]}" stroke-width="3" points="{" ".join(coords)}"/><text x="{45 + index * 180}" y="205" fill="{colors[index % len(colors)]}">{escape(name)}</text>')
        chart = f'<svg viewBox="0 0 580 220" width="100%" role="img" aria-label="Weekly average prices">{"".join(points)}<line x1="40" y1="170" x2="540" y2="170" stroke="#ccd3da"/><text x="40" y="195" fill="#667">{escape(weeks[0])}</text><text x="475" y="195" fill="#667">{escape(weeks[-1])}</text></svg>'
    else:
        chart = '<p>No chart data yet.</p>'
    return f'''<!doctype html><html><body style="font-family:Arial,sans-serif;color:#17212b">
<h2>Organic EU Meat Research — Weekly Update</h2>
<p>Verified suppliers: <b>{verified_suppliers}</b> · Recorded suppliers/leads: <b>{suppliers}</b> · Unverified leads: <b>{unverified_leads}</b> · New candidates: <b>{new_suppliers}</b></p>
<h3>Price movement</h3>{chart}
<table cellpadding="8" cellspacing="0" border="1" style="border-collapse:collapse">
<tr><th>Week</th><th>Country</th><th>Product</th><th>Average</th><th>Change</th><th>Samples</th></tr>{table}</table>
<h3>Published candidate price signals (excluded from verified statistics)</h3>
<table cellpadding="8" cellspacing="0" border="1" style="border-collapse:collapse">
<tr><th>Date</th><th>Country</th><th>Supplier</th><th>Product</th><th>Price</th></tr>{lead_price_table}</table>
<p style="color:#667">Delivery costs are not added. Retail and unverified organic records are excluded from price statistics.</p>
</body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/research-wife.db')
    parser.add_argument('--output', default='data/exports/weekly-email.html')
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.database) as db:
        output.write_text(build_email(db), encoding='utf-8')
    print(f'Generated {output}')


if __name__ == '__main__':
    main()
