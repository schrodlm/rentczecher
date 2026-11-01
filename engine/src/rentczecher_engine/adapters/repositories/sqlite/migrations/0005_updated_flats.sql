-- When a scan last found a viewed flat changed: a portal newly posting it or
-- a posting's new price. Viewing the flat again clears it.
ALTER TABLE property_tracking ADD COLUMN updated_at TEXT;
