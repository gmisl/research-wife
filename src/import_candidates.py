"""Import reviewed candidate JSON without promoting it to verified status."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/research-wife.db')
    parser.add_argument('--input', default='data/initial_candidates.json')
    args = parser.parse_args()
    candidates = json.loads(Path(args.input).read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(args.database) as db:
        for item in candidates:
            db.execute(
                """INSERT OR IGNORE INTO suppliers
                (legal_name,country_code,address,website,official_email,official_phone,
                 supplier_type,priority_class,status,first_seen_at,last_seen_at,last_verified_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item['legal_name'],item['country_code'],item['official_contact'].get('address'),
                 item['official_contact'].get('website'),item['official_contact'].get('email'),
                 item['official_contact'].get('phone'),item['supplier_type'],item['priority_class'],
                 item['status'],item['checked_at'],item['checked_at'],None),
            )
            supplier_id = db.execute(
                "SELECT id FROM suppliers WHERE legal_name=? AND country_code=?",
                (item['legal_name'], item['country_code']),
            ).fetchone()[0]
            product_id = db.execute(
                "SELECT id FROM products WHERE product_family=? AND category_code=?",
                (item['product_family'], item['category_code']),
            ).fetchone()
            if not product_id:
                db.execute(
                    "INSERT INTO products(product_family,category_code,category_name,frozen,form) VALUES(?,?,?,?,?)",
                    (item['product_family'],item['category_code'],item['product_description'],1,'block'),
                )
                product_id = (db.execute('SELECT last_insert_rowid()').fetchone()[0],)
            db.execute(
                """INSERT OR IGNORE INTO supplier_products
                (supplier_id,product_id,product_description,pallet_weight_kg,wholesale_evidence,
                 availability_status,first_seen_at,last_seen_at)
                VALUES(?,?,?,?,?,?,?,?)""",
                (supplier_id,product_id[0],item['product_description'],570,1,'unverified',item['checked_at'],item['checked_at']),
            )
            for url in item['sources']:
                db.execute(
                    "INSERT OR IGNORE INTO evidence_sources(url,canonical_url,domain,source_type,country_code,retrieved_at,reliability_score) VALUES(?,?,?,?,?,?,?)",
                    (url,url,url.split('/')[2],'supplier_website',item['country_code'],item['checked_at'],0.75),
                )
                evidence_id = db.execute('SELECT id FROM evidence_sources WHERE canonical_url=?',(url,)).fetchone()[0]
                db.execute(
                    "INSERT INTO evidence_links(evidence_source_id,entity_type,entity_id,field_name,confidence,notes) VALUES(?,?,?,?,?,?)",
                    (evidence_id,'supplier',supplier_id,'candidate_source',0.75,item.get('notes')),
                )
            if item.get('price',{}).get('price_status') == 'published':
                price = item['price']
                db.execute(
                    """INSERT INTO prices
                    (supplier_id,product_id,price_status,price_value,price_currency,price_eur,price_unit,price_date,is_wholesale,vat_status,notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (supplier_id,product_id[0],'published',price['value'],price['currency'],price['value'],price['unit'],item['checked_at'],1,'excluded',item.get('notes')),
                )
        db.commit()
    print(f'Imported {len(candidates)} candidates into {args.database}')


if __name__ == '__main__':
    main()
