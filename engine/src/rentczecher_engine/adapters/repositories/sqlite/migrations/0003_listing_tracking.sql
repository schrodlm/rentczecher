-- A listing row is a fact of the portal posting and is shared by every
-- profile whose search sees it. Per-profile state (when it was seen, how
-- many scrapes have missed it) lives in listing_tracking. No deployed
-- database predates this migration, so the listings table is recreated
-- empty instead of copied.
DROP TABLE listings;

CREATE TABLE listings (
    id          TEXT PRIMARY KEY,               -- "source:source_id"
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    source      TEXT NOT NULL CHECK (source IN ('sreality', 'bezrealitky', 'remax')),
    url         TEXT NOT NULL,
    scraped_at  TEXT NOT NULL
);

CREATE TABLE listing_tracking (
    profile_id    TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    listing_id    TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    first_seen_at TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL,
    miss_count    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (profile_id, listing_id)
);

CREATE INDEX idx_listing_tracking_listing ON listing_tracking(listing_id);
