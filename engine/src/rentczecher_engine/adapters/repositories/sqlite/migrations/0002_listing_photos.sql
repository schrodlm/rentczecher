-- A listing's gallery, one row per photo in the portal's order. The file is
-- known only once it is downloaded. A download that fails counts an attempt,
-- and a photo whose attempts run out is given up.
CREATE TABLE listing_photos (
    listing_id TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    position   INTEGER NOT NULL CHECK (position >= 0),
    source_url TEXT NOT NULL,
    file_key   TEXT UNIQUE,
    attempts   INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    PRIMARY KEY (listing_id, position)
);

-- The flats whose whole gallery a user asked for, by opening or starring
-- one. Every other listing keeps only its main photo.
CREATE TABLE gallery_requests (
    property_id  TEXT PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
    requested_at TEXT NOT NULL
);

DROP TABLE property_images;
