-- The portal's location text as scraped, named apart from the resolved
-- property_locations.
ALTER TABLE properties RENAME COLUMN location TO location_raw_text;
