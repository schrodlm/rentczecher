-- The gazetteer: every official Czech place the app works with, keyed by its
-- RÚIAN code, plus how each portal names the places it can search by.
--
-- A RÚIAN code is unique only within one kind, so a place is identified by
-- its kind and its code together. name_norm is the lowercase name without
-- diacritics that the resolver looks up.

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- The places, one table per kind. A strict parent is a foreign key. lat and
-- lon are the mean position of the place's address points.

CREATE TABLE kraje (
    code      INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    name_norm TEXT NOT NULL,
    lat       REAL NOT NULL,
    lon       REAL NOT NULL
);

CREATE TABLE okresy (
    code      INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    name_norm TEXT NOT NULL,
    kraj_code INTEGER NOT NULL REFERENCES kraje(code),
    lat       REAL NOT NULL,
    lon       REAL NOT NULL
);

-- Praha belongs to no okres, so an obec carries its kraj directly. For every
-- other obec it is the kraj of its okres, which the build verifies.
CREATE TABLE obce (
    code       INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    name_norm  TEXT NOT NULL,
    okres_code INTEGER REFERENCES okresy(code),
    kraj_code  INTEGER NOT NULL REFERENCES kraje(code),
    lat        REAL NOT NULL,
    lon        REAL NOT NULL
);

-- Praha 1 to Praha 10.
CREATE TABLE obvody (
    code      INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    name_norm TEXT NOT NULL,
    obec_code INTEGER NOT NULL REFERENCES obce(code),
    lat       REAL NOT NULL,
    lon       REAL NOT NULL
);

-- Self-governing districts of Praha and the divided statutory cities. In
-- Praha each lies in exactly one obvod.
CREATE TABLE mestske_casti (
    code       INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    name_norm  TEXT NOT NULL,
    obec_code  INTEGER NOT NULL REFERENCES obce(code),
    obvod_code INTEGER REFERENCES obvody(code),
    lat        REAL NOT NULL,
    lon        REAL NOT NULL
);

CREATE TABLE casti_obce (
    code      INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    name_norm TEXT NOT NULL,
    obec_code INTEGER NOT NULL REFERENCES obce(code),
    lat       REAL NOT NULL,
    lon       REAL NOT NULL
);

CREATE TABLE ulice (
    code      INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    name_norm TEXT NOT NULL,
    obec_code INTEGER NOT NULL REFERENCES obce(code),
    lat       REAL NOT NULL,
    lon       REAL NOT NULL
);

CREATE INDEX idx_obce_name ON obce(name_norm);
CREATE INDEX idx_obvody_name ON obvody(name_norm);
CREATE INDEX idx_mestske_casti_name ON mestske_casti(name_norm);
CREATE INDEX idx_casti_obce_name ON casti_obce(name_norm);
CREATE INDEX idx_ulice_name ON ulice(name_norm);
CREATE INDEX idx_obce_okres ON obce(okres_code);
CREATE INDEX idx_casti_obce_obec ON casti_obce(obec_code);
CREATE INDEX idx_ulice_obec ON ulice(obec_code);

-- The overlaps, each pair seen together on at least one address point. Only
-- links to a městská část are stored: its obvod follows from it.

CREATE TABLE casti_obce_mestske_casti (
    cast_obce_code    INTEGER NOT NULL REFERENCES casti_obce(code),
    mestska_cast_code INTEGER NOT NULL REFERENCES mestske_casti(code),
    PRIMARY KEY (cast_obce_code, mestska_cast_code)
);

CREATE TABLE ulice_mestske_casti (
    ulice_code        INTEGER NOT NULL REFERENCES ulice(code),
    mestska_cast_code INTEGER NOT NULL REFERENCES mestske_casti(code),
    PRIMARY KEY (ulice_code, mestska_cast_code)
);

CREATE TABLE ulice_casti_obce (
    ulice_code     INTEGER NOT NULL REFERENCES ulice(code),
    cast_obce_code INTEGER NOT NULL REFERENCES casti_obce(code),
    PRIMARY KEY (ulice_code, cast_obce_code)
);

-- How each portal names the places it can search by: a region is a kraj, a
-- district is an okres or, in Praha, an obvod.

CREATE TABLE sreality_regions (
    kraj_code INTEGER PRIMARY KEY REFERENCES kraje(code),
    region_id INTEGER NOT NULL
);

CREATE TABLE sreality_districts (
    okres_code  INTEGER UNIQUE REFERENCES okresy(code),
    obvod_code  INTEGER UNIQUE REFERENCES obvody(code),
    district_id INTEGER NOT NULL,
    CHECK ((okres_code IS NULL) <> (obvod_code IS NULL))
);

CREATE TABLE remax_regions (
    kraj_code INTEGER PRIMARY KEY REFERENCES kraje(code),
    region_id INTEGER NOT NULL
);

CREATE TABLE remax_districts (
    okres_code  INTEGER UNIQUE REFERENCES okresy(code),
    obvod_code  INTEGER UNIQUE REFERENCES obvody(code),
    region_id   INTEGER NOT NULL,
    district_id INTEGER NOT NULL,
    CHECK ((okres_code IS NULL) <> (obvod_code IS NULL))
);

CREATE TABLE bezrealitky_regions (
    kraj_code     INTEGER PRIMARY KEY REFERENCES kraje(code),
    region_osm_id TEXT NOT NULL
);

CREATE TABLE bezrealitky_districts (
    okres_code    INTEGER UNIQUE REFERENCES okresy(code),
    obvod_code    INTEGER UNIQUE REFERENCES obvody(code),
    region_osm_id TEXT NOT NULL,
    CHECK ((okres_code IS NULL) <> (obvod_code IS NULL))
);

-- Every place a listing's text can name, by name, for the resolver: each
-- row with its kind and code, its obec code, and its obec and okres names for
-- context matching.
CREATE VIEW places AS
    SELECT 'ulice' AS kind, u.code, u.name, u.name_norm,
           o.code AS obec_code, o.name_norm AS obec_norm,
           ok.name_norm AS okres_norm, u.lat, u.lon
    FROM ulice u
    JOIN obce o ON o.code = u.obec_code
    LEFT JOIN okresy ok ON ok.code = o.okres_code
UNION ALL
    SELECT 'cast_obce' AS kind, c.code, c.name, c.name_norm,
           o.code, o.name_norm, ok.name_norm, c.lat, c.lon
    FROM casti_obce c
    JOIN obce o ON o.code = c.obec_code
    LEFT JOIN okresy ok ON ok.code = o.okres_code
UNION ALL
    SELECT 'mestska_cast' AS kind, m.code, m.name, m.name_norm,
           o.code, o.name_norm, ok.name_norm, m.lat, m.lon
    FROM mestske_casti m
    JOIN obce o ON o.code = m.obec_code
    LEFT JOIN okresy ok ON ok.code = o.okres_code
UNION ALL
    SELECT 'obec' AS kind, o.code, o.name, o.name_norm,
           o.code, o.name_norm, ok.name_norm, o.lat, o.lon
    FROM obce o
    LEFT JOIN okresy ok ON ok.code = o.okres_code
UNION ALL
    SELECT 'okres' AS kind, ok.code, ok.name, ok.name_norm,
           NULL, NULL, ok.name_norm, ok.lat, ok.lon
    FROM okresy ok;
