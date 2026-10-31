-- A listing's source references the portals table, so admitting a portal is
-- one row there. SQLite cannot change a column's constraint in place, so the
-- table is rebuilt.
CREATE TABLE listings_new (
    id          TEXT PRIMARY KEY,               -- "source:source_id"
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    source      TEXT NOT NULL REFERENCES portals(name),
    url         TEXT NOT NULL,
    scraped_at  TEXT NOT NULL
);

-- Rowids carry over, since the migration runner tells a row it orphaned from
-- one orphaned before by its rowid.
INSERT INTO listings_new (rowid, id, property_id, source, url, scraped_at)
SELECT rowid, id, property_id, source, url, scraped_at FROM listings;

DROP TABLE listings;

ALTER TABLE listings_new RENAME TO listings;
