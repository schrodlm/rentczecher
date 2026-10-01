-- A favourited listing is the user's to keep: the prune sweep never forgets
-- its tracking row, so it stays seen for as long as the user wants. NULL
-- means not favourited. Favouriting is per profile, like all tracking.
ALTER TABLE listing_tracking ADD COLUMN favourited_at TEXT;
