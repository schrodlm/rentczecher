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
