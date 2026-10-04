-- Every layout a property can have, keyed by its canonical code.
CREATE TABLE dispositions (
    code       TEXT PRIMARY KEY,
    rooms      INTEGER,
    kitchen    TEXT CHECK (kitchen IN ('kitchenette', 'separate')),
    CHECK ((rooms IS NULL) = (kitchen IS NULL))
);

INSERT INTO dispositions (code, rooms, kitchen) VALUES
    ('1+kk', 1, 'kitchenette'),
    ('1+1', 1, 'separate'),
    ('2+kk', 2, 'kitchenette'),
    ('2+1', 2, 'separate'),
    ('3+kk', 3, 'kitchenette'),
    ('3+1', 3, 'separate'),
    ('4+kk', 4, 'kitchenette'),
    ('4+1', 4, 'separate'),
    ('5+kk', 5, 'kitchenette'),
    ('5+1', 5, 'separate'),
    ('6+kk', 6, 'kitchenette'),
    ('6+1', 6, 'separate'),
    ('7+kk', 7, 'kitchenette'),
    ('7+1', 7, 'separate'),
    ('8+kk', 8, 'kitchenette'),
    ('8+1', 8, 'separate'),
    ('9+kk', 9, 'kitchenette'),
    ('9+1', 9, 'separate'),
    ('atypicky', NULL, NULL);

ALTER TABLE properties ADD COLUMN disposition_code TEXT REFERENCES dispositions(code);

-- SQLite's lower() folds ASCII only, so the accented spellings are listed
-- in both cases of their accented letter. Text naming no layout stays NULL.
UPDATE properties SET disposition_code = CASE
    WHEN replace(lower(disposition_raw_text), ' ', '')
        IN ('garsoniéra', 'garsoniÉra', 'garsoniera', 'garsonka') THEN '1+kk'
    WHEN replace(lower(disposition_raw_text), ' ', '')
        IN ('atypický', 'atypickÝ', 'atypicky') THEN 'atypicky'
    ELSE (
        SELECT code FROM dispositions
        WHERE code = replace(lower(disposition_raw_text), ' ', '')
    )
END;
