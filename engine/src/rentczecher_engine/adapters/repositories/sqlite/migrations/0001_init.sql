-- TEXT timestamps are UTC ISO 8601, "+00:00"-suffixed (so MAX()/ORDER BY is chronological).
-- foreign_keys=ON must be set before any transaction opens (it no-ops mid-transaction);
-- WAL and busy_timeout are set at connect time too.

-- The fixed vocabularies the other tables reference.

CREATE TABLE portals (
    name TEXT PRIMARY KEY
);

INSERT INTO portals (name) VALUES ('sreality'), ('bezrealitky'), ('remax');

CREATE TABLE offer_types (
    name TEXT PRIMARY KEY
);

INSERT INTO offer_types (name) VALUES ('rent'), ('sale');

CREATE TABLE estate_types (
    name TEXT PRIMARY KEY
);

INSERT INTO estate_types (name) VALUES ('flat'), ('house'), ('land'), ('cottage');

CREATE TABLE place_kinds (
    name TEXT PRIMARY KEY
);

INSERT INTO place_kinds (name) VALUES
    ('kraj'), ('okres'), ('obec'), ('obvod'), ('mestska_cast'), ('cast_obce'), ('ulice');

-- Every layout a property can have, keyed by its canonical code.
CREATE TABLE dispositions (
    code       TEXT PRIMARY KEY,
    rooms      INTEGER,
    kitchen    TEXT CHECK (kitchen IN ('kitchenette', 'separate')),
    CHECK ((rooms IS NULL) = (kitchen IS NULL))
);

INSERT INTO dispositions (code, rooms, kitchen) VALUES
    ('1+kk', 1, 'kitchenette'),
    ('1+1', 1, 'separate'),
    ('2+kk', 2, 'kitchenette'),
    ('2+1', 2, 'separate'),
    ('3+kk', 3, 'kitchenette'),
    ('3+1', 3, 'separate'),
    ('4+kk', 4, 'kitchenette'),
    ('4+1', 4, 'separate'),
    ('5+kk', 5, 'kitchenette'),
    ('5+1', 5, 'separate'),
    ('6+kk', 6, 'kitchenette'),
    ('6+1', 6, 'separate'),
    ('7+kk', 7, 'kitchenette'),
    ('7+1', 7, 'separate'),
    ('8+kk', 8, 'kitchenette'),
    ('8+1', 8, 'separate'),
    ('9+kk', 9, 'kitchenette'),
    ('9+1', 9, 'separate'),
    ('atypicky', NULL, NULL);

-- Profiles: one saved search each, with its criteria, portals and preferences.

CREATE TABLE profiles (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    paused_at  TEXT
);

-- A null bound is no bound.
CREATE TABLE profile_criteria (
    profile_id  TEXT PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
    offer_type  TEXT NOT NULL REFERENCES offer_types(name),
    estate_type TEXT NOT NULL REFERENCES estate_types(name),
    place_kind  TEXT NOT NULL REFERENCES place_kinds(name),
    place_code  INTEGER NOT NULL,
    min_price   INTEGER CHECK (min_price > 0),
    max_price   INTEGER CHECK (max_price > 0),
    min_size_m2 INTEGER CHECK (min_size_m2 > 0),
    max_size_m2 INTEGER CHECK (max_size_m2 > 0),
    min_land_m2 INTEGER CHECK (min_land_m2 > 0),
    CHECK (min_price IS NULL OR max_price IS NULL OR min_price <= max_price),
    CHECK (min_size_m2 IS NULL OR max_size_m2 IS NULL OR min_size_m2 <= max_size_m2)
);

-- No accepted disposition accepts any.
CREATE TABLE accepted_dispositions (
    profile_id  TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    disposition TEXT NOT NULL REFERENCES dispositions(code),
    PRIMARY KEY (profile_id, disposition)
);

CREATE TABLE profile_portals (
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    portal     TEXT NOT NULL REFERENCES portals(name),
    PRIMARY KEY (profile_id, portal)
);

-- A preferred list lives in its own table, where a CHECK here cannot see
-- whether a weight has one.
CREATE TABLE profile_preferences (
    profile_id          TEXT PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
    price_per_m2_weight REAL NOT NULL,
    disposition_weight  REAL NOT NULL,
    size_weight         REAL NOT NULL,
    preferred_size_m2   INTEGER,
    place_weight        REAL NOT NULL,
    land_weight         REAL NOT NULL,
    preferred_land_m2   INTEGER,
    price_weight        REAL NOT NULL,
    preferred_price     INTEGER,
    CHECK (size_weight = 0 OR (preferred_size_m2 IS NOT NULL AND preferred_size_m2 > 0)),
    CHECK (land_weight = 0 OR (preferred_land_m2 IS NOT NULL AND preferred_land_m2 > 0)),
    CHECK (price_weight = 0 OR (preferred_price IS NOT NULL AND preferred_price > 0))
);

-- Rank 1 is the most preferred.
CREATE TABLE preferred_dispositions (
    profile_id  TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    disposition TEXT NOT NULL REFERENCES dispositions(code),
    rank        INTEGER NOT NULL CHECK (rank >= 1),
    PRIMARY KEY (profile_id, disposition),
    UNIQUE (profile_id, rank)
);

CREATE TABLE preferred_places (
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    place_kind TEXT NOT NULL REFERENCES place_kinds(name),
    place_code INTEGER NOT NULL,
    rank       INTEGER NOT NULL CHECK (rank >= 1),
    PRIMARY KEY (profile_id, place_kind, place_code),
    UNIQUE (profile_id, rank)
);

-- Properties: the real-world units, shared by every profile.

-- cell_lat/cell_lon are the domain geocell() of the property's canonical
-- lat/lon, not raw coordinates - a property with no locatable listing has
-- no cell, and changing the grid constants in domain/geo.py invalidates
-- every stored cell.
CREATE TABLE properties (
    id                   TEXT PRIMARY KEY,
    created_at           TEXT NOT NULL,
    merged_into          TEXT REFERENCES properties(id),   -- null = live; set = folded into that property
    title                TEXT,
    location_raw_text    TEXT,
    size_m2              INTEGER,
    disposition_raw_text TEXT,
    lat                  REAL,
    lon                  REAL,
    land_m2              INTEGER,
    cell_lat             INTEGER,
    cell_lon             INTEGER,
    disposition_code     TEXT REFERENCES dispositions(code)
);
CREATE INDEX idx_properties_cell ON properties(cell_lat, cell_lon);

-- Where a property lies: the RÚIAN unit of each kind its listing's text
-- named, by code, a code being unique only within its kind. The units
-- themselves live in the shipped gazetteer, a separate file, so no foreign
-- key can reach them: a code the gazetteer no longer holds reads back as
-- unknown.
--
-- The house number as the portal gave it, when it gave one: číslo popisné
-- (unique within its část obce) and číslo orientační (unique within its
-- street, sometimes with a letter, such as 14a).
CREATE TABLE property_locations (
    property_id       TEXT PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
    kraj_code         INTEGER NOT NULL,
    okres_code        INTEGER,
    obec_code         INTEGER,
    obvod_code        INTEGER,
    mestska_cast_code INTEGER,
    cast_obce_code    INTEGER,
    ulice_code        INTEGER,
    cislo_popisne     TEXT,
    cislo_orientacni  TEXT
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

-- Listings: one portal's posting of a property each, a fact shared by every
-- profile whose search sees it.

CREATE TABLE listings (
    id          TEXT PRIMARY KEY,               -- "source:source_id"
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    source      TEXT NOT NULL CHECK (source IN ('sreality', 'bezrealitky', 'remax')),
    url         TEXT NOT NULL,
    scraped_at  TEXT NOT NULL
);

-- What a profile's scans know of a listing: when they first and last saw it,
-- and how often they have missed it since.
CREATE TABLE listing_tracking (
    profile_id    TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    listing_id    TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    first_seen_at TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL,
    miss_count    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (profile_id, listing_id)
);
CREATE INDEX idx_listing_tracking_listing ON listing_tracking(listing_id);

-- What a profile did with a flat, once per flat rather than on each of its
-- listings: viewing or starring a flat posted on two portals is one act.
CREATE TABLE property_tracking (
    profile_id    TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    property_id   TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    viewed_at     TEXT,
    favourited_at TEXT,
    PRIMARY KEY (profile_id, property_id)
);

-- Scans and what they observed.

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
CREATE INDEX idx_dedup_records_listing ON dedup_records(listing_id);
