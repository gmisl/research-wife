PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY,
    legal_name TEXT NOT NULL,
    trading_name TEXT,
    country_code TEXT NOT NULL CHECK(length(country_code) = 2),
    region TEXT,
    address TEXT,
    website TEXT,
    official_email TEXT,
    official_phone TEXT,
    supplier_type TEXT NOT NULL CHECK(supplier_type IN (
        'producer','processor','producer_processor','distributor','wholesaler',
        'exporter','cooperative','other'
    )),
    priority_class TEXT NOT NULL DEFAULT 'primary' CHECK(priority_class IN ('primary','secondary')),
    status TEXT NOT NULL DEFAULT 'new' CHECK(status IN (
        'new','active','needs_recheck','inactive_confirmed','lost_certification','unverified','rejected'
    )),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    last_verified_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(legal_name, country_code)
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    product_family TEXT NOT NULL CHECK(product_family IN ('beef','chicken')),
    category_code TEXT NOT NULL,
    category_name TEXT NOT NULL,
    frozen INTEGER NOT NULL DEFAULT 1 CHECK(frozen IN (0,1)),
    form TEXT NOT NULL CHECK(form IN ('block','bulk','other')),
    description TEXT,
    UNIQUE(product_family, category_code)
);

CREATE TABLE IF NOT EXISTS supplier_products (
    id INTEGER PRIMARY KEY,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    product_description TEXT,
    pack_weight_kg REAL,
    pallet_weight_kg REAL,
    pallets_per_order REAL,
    moq_kg REAL,
    moq_pallets REAL,
    wholesale_evidence INTEGER NOT NULL DEFAULT 0 CHECK(wholesale_evidence IN (0,1)),
    availability_status TEXT NOT NULL DEFAULT 'unverified' CHECK(availability_status IN ('active','needs_recheck','inactive','unverified')),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE(supplier_id, product_id)
);

CREATE TABLE IF NOT EXISTS certifications (
    id INTEGER PRIMARY KEY,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    certification_scheme TEXT NOT NULL,
    certification_body TEXT NOT NULL,
    certificate_number TEXT,
    valid_from TEXT,
    valid_until TEXT,
    status TEXT NOT NULL CHECK(status IN ('verified','expired','suspended','unverified')),
    verification_source_id INTEGER,
    verified_at TEXT,
    UNIQUE(supplier_id, certification_body, certificate_number)
);

CREATE TABLE IF NOT EXISTS evidence_sources (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    canonical_url TEXT,
    domain TEXT,
    source_type TEXT NOT NULL CHECK(source_type IN (
        'government_registry','certification_registry','supplier_website',
        'b2b_marketplace','trade_portal','price_index','industry_news','search_result','other'
    )),
    country_code TEXT,
    language_code TEXT,
    title TEXT,
    retrieved_at TEXT NOT NULL,
    published_at TEXT,
    http_status INTEGER,
    content_hash TEXT,
    reliability_score REAL CHECK(reliability_score BETWEEN 0 AND 1),
    raw_snapshot_path TEXT,
    UNIQUE(canonical_url)
);

CREATE TABLE IF NOT EXISTS evidence_links (
    id INTEGER PRIMARY KEY,
    evidence_source_id INTEGER NOT NULL REFERENCES evidence_sources(id),
    entity_type TEXT NOT NULL CHECK(entity_type IN ('supplier','product','supplier_product','certification','price','event')),
    entity_id INTEGER NOT NULL,
    field_name TEXT,
    extracted_value TEXT,
    confidence REAL CHECK(confidence BETWEEN 0 AND 1),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    price_status TEXT NOT NULL CHECK(price_status IN ('published','quote_required','indicative','unavailable')),
    price_value REAL,
    price_currency TEXT,
    price_eur REAL,
    price_unit TEXT CHECK(price_unit IN ('EUR/kg','EUR/tonne','EUR/pallet','EUR/unit')),
    price_date TEXT,
    is_wholesale INTEGER NOT NULL DEFAULT 0 CHECK(is_wholesale IN (0,1)),
    vat_status TEXT CHECK(vat_status IN ('included','excluded','unknown')),
    incoterm TEXT,
    delivery_cost_included INTEGER CHECK(delivery_cost_included IN (0,1)),
    pack_weight_kg REAL,
    moq_kg REAL,
    moq_pallets REAL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prices_product_date ON prices(product_id, price_date);
CREATE INDEX IF NOT EXISTS idx_suppliers_country_status ON suppliers(country_code, status);
CREATE INDEX IF NOT EXISTS idx_evidence_type_country ON evidence_sources(source_type, country_code);

CREATE TABLE IF NOT EXISTS search_runs (
    id INTEGER PRIMARY KEY,
    run_type TEXT NOT NULL CHECK(run_type IN ('initial','weekly','manual')),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    date_from TEXT NOT NULL,
    date_to TEXT NOT NULL,
    countries_requested TEXT NOT NULL,
    languages_requested TEXT NOT NULL,
    queries_attempted INTEGER DEFAULT 0,
    sources_collected INTEGER DEFAULT 0,
    suppliers_found INTEGER DEFAULT 0,
    prices_found INTEGER DEFAULT 0,
    errors TEXT,
    status TEXT NOT NULL DEFAULT 'running' CHECK(status IN ('running','completed','failed','partial'))
);

CREATE TABLE IF NOT EXISTS search_attempts (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES search_runs(id),
    country_code TEXT NOT NULL,
    language_code TEXT NOT NULL,
    query TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    result_count INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS supplier_events (
    id INTEGER PRIMARY KEY,
    supplier_id INTEGER REFERENCES suppliers(id),
    product_id INTEGER REFERENCES products(id),
    event_type TEXT NOT NULL CHECK(event_type IN (
        'new_supplier','new_product','price_change','certification_verified',
        'certification_expired','certification_restored','contact_change',
        'availability_change','status_change'
    )),
    old_value TEXT,
    new_value TEXT,
    detected_at TEXT NOT NULL,
    evidence_source_id INTEGER REFERENCES evidence_sources(id),
    notified INTEGER NOT NULL DEFAULT 0 CHECK(notified IN (0,1))
);

CREATE TABLE IF NOT EXISTS weekly_market_stats (
    id INTEGER PRIMARY KEY,
    week_start TEXT NOT NULL,
    week_end TEXT NOT NULL,
    country_code TEXT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    avg_price_eur REAL,
    median_price_eur REAL,
    min_price_eur REAL,
    max_price_eur REAL,
    sample_count INTEGER NOT NULL DEFAULT 0,
    supplier_count INTEGER NOT NULL DEFAULT 0,
    previous_avg_price_eur REAL,
    change_pct REAL,
    trend_direction TEXT CHECK(trend_direction IN ('up','down','stable','volatile','insufficient_data')),
    UNIQUE(week_start, country_code, product_id)
);

CREATE TABLE IF NOT EXISTS rejected_candidates (
    id INTEGER PRIMARY KEY,
    run_id INTEGER REFERENCES search_runs(id),
    name TEXT,
    country_code TEXT,
    reason_code TEXT NOT NULL,
    source_url TEXT,
    notes TEXT,
    rejected_at TEXT NOT NULL
);

INSERT OR IGNORE INTO products(id, product_family, category_code, category_name, frozen, form)
VALUES
    (1, 'beef', 'frozen_minced_beef_blocks', 'Frozen minced beef blocks', 1, 'block'),
    (2, 'chicken', 'frozen_minced_chicken_blocks', 'Frozen minced chicken blocks', 1, 'block');
