-- The portal's disposition text as scraped, named apart from the parsed
-- Disposition layout.
ALTER TABLE properties RENAME COLUMN disposition TO disposition_raw_text;
