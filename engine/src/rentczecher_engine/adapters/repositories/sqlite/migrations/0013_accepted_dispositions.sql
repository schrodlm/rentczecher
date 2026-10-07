-- Criteria name the dispositions they accept instead of a room range and a
-- kitchen kind. A range converts to the dispositions it covered, and no range
-- to none, which accepts any. An atypical disposition is accepted only once
-- named, where the range let it through.
CREATE TABLE accepted_dispositions (
    profile_id  TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    disposition TEXT NOT NULL REFERENCES dispositions(code),
    PRIMARY KEY (profile_id, disposition)
);
INSERT INTO accepted_dispositions (profile_id, disposition)
SELECT c.profile_id, d.code
FROM profile_criteria c
JOIN dispositions d ON d.rooms IS NOT NULL
WHERE (c.min_rooms IS NOT NULL OR c.max_rooms IS NOT NULL OR c.kitchen IS NOT NULL)
  AND d.rooms BETWEEN coalesce(c.min_rooms, 1) AND coalesce(c.max_rooms, 9)
  AND (c.kitchen IS NULL OR d.kitchen = c.kitchen);

-- SQLite cannot drop a column a CHECK names, so the table is rebuilt.
CREATE TABLE profile_criteria_rebuilt (
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
INSERT INTO profile_criteria_rebuilt
    (profile_id, offer_type, estate_type, place_kind, place_code, min_price, max_price,
     min_size_m2, max_size_m2, min_land_m2)
SELECT profile_id, offer_type, estate_type, place_kind, place_code, min_price, max_price,
       min_size_m2, max_size_m2, min_land_m2
FROM profile_criteria;
DROP TABLE profile_criteria;
ALTER TABLE profile_criteria_rebuilt RENAME TO profile_criteria;
