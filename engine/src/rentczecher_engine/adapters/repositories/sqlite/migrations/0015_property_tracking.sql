-- What a profile did with a flat, once per flat rather than on each of its
-- listings: viewing or starring a flat posted on two portals is one act. A
-- flat is viewed and starred since the first of its listings was.
CREATE TABLE property_tracking (
    profile_id    TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    property_id   TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    viewed_at     TEXT,
    favourited_at TEXT,
    PRIMARY KEY (profile_id, property_id)
);

INSERT INTO property_tracking (profile_id, property_id, viewed_at, favourited_at)
SELECT listing_tracking.profile_id, listings.property_id,
       min(listing_tracking.viewed_at), min(listing_tracking.favourited_at)
FROM listing_tracking
JOIN listings ON listings.id = listing_tracking.listing_id
GROUP BY listing_tracking.profile_id, listings.property_id;
