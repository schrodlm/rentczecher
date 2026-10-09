-- Each preference's setting is named for what it is: the preferred value.
ALTER TABLE profile_preferences RENAME COLUMN max_good_price TO preferred_price;
ALTER TABLE profile_preferences RENAME COLUMN ideal_size_m2 TO preferred_size_m2;
ALTER TABLE profile_preferences RENAME COLUMN ideal_land_m2 TO preferred_land_m2;
