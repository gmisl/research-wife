"""Populate a disposable local database with clearly labelled demo data."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import date, timedelta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/demo.db')
    args = parser.parse_args()
    with sqlite3.connect(args.database) as db:
        db.executescript(open('schema.sql', encoding='utf-8').read())
        now = date.today().isoformat()
        db.executemany(
            "INSERT OR IGNORE INTO suppliers(legal_name,country_code,supplier_type,priority_class,status,first_seen_at,last_seen_at,last_verified_at,website) VALUES(?,?,?,?,?,?,?,?,?)",
            [
                ('Demo Organic Beef Producer GmbH','DE','producer_processor','primary','active',now,now,now,'https://example.com/beef'),
                ('Demo Organic Chicken Foods S.A.','ES','producer','primary','active',now,now,now,'https://example.com/chicken'),
                ('Demo Organic Distribution BV','NL','distributor','secondary','unverified',now,now,None,'https://example.com/distributor'),
            ],
        )
        suppliers = {r[0]: r[1] for r in db.execute('SELECT legal_name,id FROM suppliers')}
        db.executemany(
            "INSERT INTO certifications(supplier_id,certification_scheme,certification_body,certificate_number,status,verified_at) VALUES(?,?,?,?,?,?)",
            [(suppliers['Demo Organic Beef Producer GmbH'],'EU organic','Demo certifier','DE-DEMO-BEEF','verified',now),
             (suppliers['Demo Organic Chicken Foods S.A.'],'EU organic','Demo certifier','ES-DEMO-CHICKEN','verified',now)],
        )
        rows = []
        for weeks, beef, chicken in [(3,8.20,6.90),(2,8.45,7.10),(1,8.65,7.25),(0,8.90,7.40)]:
            d = date.today() - timedelta(days=weeks * 7 + 2)
            rows += [(suppliers['Demo Organic Beef Producer GmbH'],1,'published',beef,'EUR/kg',d.isoformat()),
                     (suppliers['Demo Organic Chicken Foods S.A.'],2,'published',chicken,'EUR/kg',d.isoformat())]
        db.executemany(
            "INSERT INTO prices(supplier_id,product_id,price_status,price_eur,price_currency,price_unit,price_date,is_wholesale) VALUES(?,?,?,?,?,?,?,1)",
            [(a,b,c,d,'EUR',e,f) for a,b,c,d,e,f in rows],
        )
        db.commit()
    print(f'Demo database created: {args.database}')


if __name__ == '__main__':
    main()
