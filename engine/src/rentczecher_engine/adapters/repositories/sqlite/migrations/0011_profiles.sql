-- Profiles become user data with their criteria and preferences stored
-- here. Rows a scan created earlier carry none, so they go, and their
-- tracking goes with them through its cascade.
DELETE FROM profiles;
ALTER TABLE profiles DROP COLUMN active;
ALTER TABLE profiles ADD COLUMN paused_at TEXT;

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
    min_land_m2 INTEGER CHECK (min_land_m2 > 0),
    min_rooms   INTEGER CHECK (min_rooms BETWEEN 1 AND 9),
    max_rooms   INTEGER CHECK (max_rooms BETWEEN 1 AND 9),
    kitchen     TEXT CHECK (kitchen IN ('kitchenette', 'separate')),
    CHECK (min_price IS NULL OR max_price IS NULL OR min_price <= max_price),
    CHECK (min_rooms IS NULL OR max_rooms IS NULL OR min_rooms <= max_rooms)
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
    ideal_size_m2       INTEGER,
    place_weight        REAL NOT NULL,
    land_weight         REAL NOT NULL,
    ideal_land_m2       INTEGER,
    price_weight        REAL NOT NULL,
    max_good_price      INTEGER,
    CHECK (size_weight = 0 OR (ideal_size_m2 IS NOT NULL AND ideal_size_m2 > 0)),
    CHECK (land_weight = 0 OR (ideal_land_m2 IS NOT NULL AND ideal_land_m2 > 0)),
    CHECK (price_weight = 0 OR (max_good_price IS NOT NULL AND max_good_price > 0))
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
