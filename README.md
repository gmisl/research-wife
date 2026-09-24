# Research Wife v2

Free, auditable weekly research system for certified organic frozen wholesale meat suppliers in the EU.

## Scope

- EU-based suppliers in all 27 member states.
- Primary focus: producers/processors offering several-pallet wholesale quantities.
- Products: frozen organic minced beef and frozen organic minced chicken, extensible to other minced-meat categories.
- Distributors are retained as secondary suppliers, never mixed with producers.
- Only certification-backed organic claims qualify as verified.
- Delivery costs are recorded only when explicitly published; they are not added to product prices.

## Planned free deployment

- GitHub Actions: weekly run.
- SQLite: historical database and weekly snapshots.
- GitHub Pages: interactive HTML dashboard.
- Gmail/Google Apps Script: weekly HTML email.

The pipeline must continue to work when no public price is available: a verified supplier can be listed with `price_status=quote_required` and excluded from price statistics.

## Current status

This repository is the new implementation base. The supplied archive contained requirements and an earlier schema, but no executable research scripts or databases.
