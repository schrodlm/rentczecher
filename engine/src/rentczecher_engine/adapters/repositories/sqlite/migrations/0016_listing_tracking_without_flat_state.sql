-- A flat's viewed and starred state lives on its property_tracking row, so a
-- listing's tracking keeps only what is its own: when the profile's scans
-- first and last saw it, and how often they have missed it since.
ALTER TABLE listing_tracking DROP COLUMN viewed_at;
ALTER TABLE listing_tracking DROP COLUMN favourited_at;
