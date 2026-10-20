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

-- The listings whose whole gallery only their advert's own page lists. The
-- page is read once, when the gallery is wanted, and a failed read counts an
-- attempt.
CREATE TABLE advert_page_reads (
    listing_id TEXT PRIMARY KEY REFERENCES listings(id) ON DELETE CASCADE,
    read_at    TEXT,
    attempts   INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0)
);

DROP TABLE property_images;

-- Each profile indexes the flats it finds, in the order it found them.
ALTER TABLE property_tracking ADD COLUMN profile_index INTEGER NOT NULL DEFAULT 0;

-- The flats already tracked are indexed in the order their rows were
-- written, which is the order the profile found them.
UPDATE property_tracking SET profile_index = (
    SELECT count(*) FROM property_tracking AS earlier
    WHERE earlier.profile_id = property_tracking.profile_id
      AND earlier.rowid <= property_tracking.rowid
);
