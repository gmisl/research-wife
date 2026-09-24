"""Generate a self-contained interactive HTML dashboard from SQLite."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from .stats import calculate_weekly_stats


ALLOWED_CATEGORIES = {
    'frozen_minced_beef', 'minced_beef_blocks', 'industrial_minced_beef',
    'frozen_minced_beef_blocks', 'minced_beef', 'industrial_minced',
    'minced_block', 'bulk_minced_beef', 'frozen_minced_chicken',
    'frozen_minced_chicken_blocks', 'industrial_minced_chicken',
    'bulk_minced_chicken',
}


def load_candidate_price_signals(path: Path) -> list[dict]:
    """Load published lead prices without mixing them into verified stats."""
    if not path.exists():
        return []
    try:
        candidates = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []
    signals = []
    for item in candidates if isinstance(candidates, list) else []:
        price = item.get('price') or {}
        if (item.get('category_code') not in ALLOWED_CATEGORIES
                or price.get('price_status') != 'published'
                or not isinstance(price.get('value'), (int, float))
                or not item.get('wholesale_evidence')
                or not item.get('official_contact', {}).get('website')):
            continue
        signals.append({
            'legal_name': item.get('legal_name', 'Unknown'),
            'country_code': item.get('country_code', ''),
            'category_code': item.get('category_code', ''),
            'description': item.get('product_description', ''),
            'price': price.get('value'),
            'currency': price.get('currency', 'EUR'),
            'unit': price.get('unit', 'EUR/kg'),
            'date': item.get('checked_at', ''),
            'website': item.get('official_contact', {}).get('website'),
            'reason': 'Lead/unverified or product form not yet comparable; excluded from verified price statistics.',
        })
    return signals


def build_dashboard(connection: sqlite3.Connection, candidate_path: Path = Path('data/initial_candidates.json')) -> str:
    stats = [asdict(x) for x in calculate_weekly_stats(connection)]
    candidate_prices = load_candidate_price_signals(candidate_path)
    suppliers = connection.execute(
        """
        SELECT s.legal_name, s.country_code, s.supplier_type, s.priority_class,
               s.status, s.website, s.last_verified_at
        FROM suppliers s
        WHERE s.status <> 'rejected'
        ORDER BY s.country_code, s.priority_class, s.legal_name
        """
    ).fetchall()
    supplier_rows = [dict(zip(
        ['legal_name','country_code','supplier_type','priority_class','status','website','last_verified_at'], row
    )) for row in suppliers]
    verified_count = sum(row['status'] == 'active' for row in supplier_rows)
    lead_count = sum(row['status'] == 'unverified' for row in supplier_rows)
    payload = json.dumps({'stats': stats, 'suppliers': supplier_rows,
                          'verifiedCount': verified_count, 'leadCount': lead_count,
                          'candidatePrices': candidate_prices}, ensure_ascii=False)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Organic EU Meat Research</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#f5f7f9;color:#17212b}}
main{{max-width:1200px;margin:auto;padding:24px}} h1{{margin-top:0}}
.cards{{display:flex;gap:12px;flex-wrap:wrap}} .card{{background:white;border-radius:10px;padding:16px;min-width:180px;box-shadow:0 1px 4px #0001}}
.controls{{background:white;padding:14px;border-radius:10px;margin:18px 0;display:flex;gap:12px;flex-wrap:wrap}}
select{{padding:8px;border:1px solid #ccd3da;border-radius:6px}} .chart{{background:white;border-radius:10px;padding:16px;margin:18px 0;min-height:350px}}
table{{border-collapse:collapse;width:100%;background:white}} th,td{{padding:9px;border-bottom:1px solid #e8ecef;text-align:left}} th{{background:#eef2f5}}
.muted{{color:#697681}} .tag{{padding:3px 7px;border-radius:10px;background:#e8f2eb}}
</style></head><body><main>
<h1>Organic EU Meat Research</h1><p class="muted">Weekly wholesale snapshot. Delivery costs are not added.</p>
<div class="cards"><div class="card"><b id="supplierCount">0</b><br><span class="muted">Suppliers / leads</span></div>
<div class="card"><b id="verifiedCount">0</b><br><span class="muted">Verified suppliers</span></div>
<div class="card"><b id="leadCount">0</b><br><span class="muted">Unverified leads</span></div>
<div class="card"><b id="countryCount">0</b><br><span class="muted">Countries</span></div>
<div class="card"><b id="priceCount">0</b><br><span class="muted">Comparable prices</span></div></div>
<div class="controls"><label>Product <select id="productFilter"><option value="all">All</option></select></label>
<label>Country <select id="countryFilter"><option value="all">All</option></select></label></div>
<section class="chart"><canvas id="priceChart"></canvas></section>
<section class="chart"><canvas id="candidatePriceChart"></canvas><p class="muted">Published candidate price signals are shown separately and are not included in verified statistics.</p></section>
<h2>Suppliers and leads</h2><div style="overflow:auto"><table><thead><tr><th>Company</th><th>Country</th><th>Type</th><th>Priority</th><th>Status</th><th>Verified</th></tr></thead><tbody id="supplierTable"></tbody></table></div>
</main><script>
const DATA={payload};
const product=document.querySelector('#productFilter'), country=document.querySelector('#countryFilter');
const products=[...new Set(DATA.stats.map(x=>x.category_name))].sort();
const countries=[...new Set(DATA.stats.map(x=>x.country_code).filter(Boolean))].sort();
products.forEach(x=>product.insertAdjacentHTML('beforeend',`<option>${{x}}</option>`));
countries.forEach(x=>country.insertAdjacentHTML('beforeend',`<option>${{x}}</option>`));
document.querySelector('#supplierCount').textContent=DATA.suppliers.length;
document.querySelector('#verifiedCount').textContent=DATA.verifiedCount;
document.querySelector('#leadCount').textContent=DATA.leadCount;
document.querySelector('#countryCount').textContent=new Set(DATA.suppliers.map(x=>x.country_code)).size;
document.querySelector('#priceCount').textContent=DATA.stats.reduce((a,x)=>a+x.sample_count,0);
let chart, candidateChart;
function render(){{const selectedProduct=product.value, selectedCountry=country.value;
 const rows=DATA.stats.filter(x=>(selectedProduct==='all'||x.category_name===selectedProduct)&&(selectedCountry==='all'||x.country_code===selectedCountry));
 const byWeek={{}}; rows.forEach(x=>(byWeek[x.week_start]??=[]).push(x)); const labels=Object.keys(byWeek).sort();
 const datasets=[...new Set(rows.map(x=>x.category_name))].map((name,i)=>({{label:name,data:labels.map(w=>{{const a=byWeek[w].filter(x=>x.category_name===name);return a.length?a.reduce((s,x)=>s+x.avg_price_eur,0)/a.length:null}}),borderColor:['#2563eb','#dc2626','#059669','#9333ea'][i%4],tension:.25,spanGaps:true}}));
 if(chart)chart.destroy(); chart=new Chart(document.querySelector('#priceChart'),{{type:'line',data:{{labels,datasets}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{title:{{display:true,text:'Average wholesale price (EUR/kg or normalized source unit)'}}}}}}}}); document.querySelector('.chart').style.height='380px';
 const leadRows=DATA.candidatePrices.filter(x=>selectedCountry==='all'||x.country_code===selectedCountry);
 if(candidateChart)candidateChart.destroy(); candidateChart=new Chart(document.querySelector('#candidatePriceChart'),{{type:'bar',data:{{labels:leadRows.map(x=>`${{x.legal_name}} (${{x.country_code}})`),datasets:[{{label:'Published lead price',data:leadRows.map(x=>x.price),backgroundColor:'#f59e0b'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{title:{{display:true,text:'Published candidate price signals — excluded from verified trend'}}}},scales:{{y:{{title:{{display:true,text:'Price'}}}}}}}}}}); 
 document.querySelector('#supplierTable').innerHTML=DATA.suppliers.filter(x=>selectedCountry==='all'||x.country_code===selectedCountry).map(x=>`<tr><td>${{x.website?`<a href="${{x.website}}" target="_blank">${{x.legal_name}}</a>`:x.legal_name}}</td><td>${{x.country_code}}</td><td>${{x.supplier_type}}</td><td><span class="tag">${{x.priority_class}}</span></td><td>${{x.status}}</td><td>${{x.last_verified_at||'—'}}</td></tr>`).join('')||'<tr><td colspan="6" class="muted">No suppliers or leads yet.</td></tr>';
}}
product.onchange=country.onchange=render; render();
</script></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/research-wife.db')
    parser.add_argument('--output', default='data/exports/dashboard.html')
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.database) as connection:
        output.write_text(build_dashboard(connection), encoding='utf-8')
    print(f'Generated {output}')


if __name__ == '__main__':
    main()
