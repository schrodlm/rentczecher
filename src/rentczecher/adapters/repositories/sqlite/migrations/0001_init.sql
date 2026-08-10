-- TEXT timestamps are UTC ISO 8601, "+00:00"-suffixed (so MAX()/ORDER BY is chronological).
-- foreign_keys=ON must be set before any transaction opens (it no-ops mid-transaction);
-- WAL and busy_timeout are set at connect time too.

CREATE TABLE profiles (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    active     INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE properties (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    merged_into TEXT REFERENCES properties(id),   -- null = live; set = folded into that property
    title       TEXT,
    location    TEXT,
    size_m2     INTEGER,
    disposition TEXT,
    lat         REAL,
    lon         REAL,
    land_m2     INTEGER
);

CREATE TABLE property_images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    url         TEXT NOT NULL,
    position    INTEGER NOT NULL DEFAULT 0,
    local_path  TEXT,
    UNIQUE (property_id, url)
);
CREATE INDEX idx_property_images_property ON property_images(property_id);

CREATE TABLE listings (
    id            TEXT PRIMARY KEY,               -- "source:source_id"
    property_id   TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    profile_id    TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    source        TEXT NOT NULL CHECK (source IN ('sreality', 'bezrealitky', 'remax')),
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    url           TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL,
    scraped_at    TEXT NOT NULL,
    miss_count    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_listings_property ON listings(property_id);
CREATE INDEX idx_listings_profile  ON listings(profile_id);

CREATE TABLE price_observations (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id         TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    price              INTEGER NOT NULL,
    charges            INTEGER,
    observed_at        TEXT NOT NULL,
    observed_in_run_id TEXT REFERENCES scrape_runs(id) ON DELETE SET NULL   -- pruning a run keeps price history
);
CREATE INDEX idx_price_obs_listing ON price_observations(listing_id, observed_at);

CREATE TABLE dedup_records (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id  TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    listing_id   TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    match_reason TEXT NOT NULL,
    differences  TEXT CHECK (differences IS NULL OR json_valid(differences)),
    decided_at   TEXT NOT NULL
);
CREATE INDEX idx_dedup_records_property ON dedup_records(property_id);
CREATE INDEX idx_dedup_records_listing  ON dedup_records(listing_id);

CREATE TABLE notification_state (
    profile_id          TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    property_id         TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    notified_at         TEXT NOT NULL,
    last_notified_price INTEGER,
    PRIMARY KEY (profile_id, property_id)
);

CREATE TABLE scrape_runs (
    id             TEXT PRIMARY KEY,
    profile_id     TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    started_at     TEXT NOT NULL,
    finished_at    TEXT,                          -- null = crashed mid-run
    status         TEXT NOT NULL CHECK (status IN ('ok', 'partial', 'failed')),
    listings_total INTEGER,
    listings_new   INTEGER,
    price_drops    INTEGER,
    disappeared    INTEGER
);
CREATE INDEX idx_scrape_runs_profile ON scrape_runs(profile_id, started_at);
