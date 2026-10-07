ALTER TABLE profile_criteria ADD COLUMN max_size_m2 INTEGER
    CHECK (max_size_m2 > 0 AND (min_size_m2 IS NULL OR min_size_m2 <= max_size_m2));
