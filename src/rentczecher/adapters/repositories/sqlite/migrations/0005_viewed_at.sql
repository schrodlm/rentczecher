-- Viewed is scrolling a listing onto the GUI's screen, distinct from
-- observed (a scrape returning it). NULL means never viewed. Viewing is per
-- profile, like the rest of listing_tracking.
ALTER TABLE listing_tracking ADD COLUMN viewed_at TEXT;
