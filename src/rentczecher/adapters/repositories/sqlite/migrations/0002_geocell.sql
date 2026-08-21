-- cell_lat/cell_lon are the domain geocell() of the property's canonical
-- lat/lon, not raw coordinates - a property with no locatable listing has
-- no cell, and changing the grid constants in domain/geo.py invalidates
-- every stored cell.

ALTER TABLE properties ADD COLUMN cell_lat INTEGER;
ALTER TABLE properties ADD COLUMN cell_lon INTEGER;

CREATE INDEX idx_properties_cell ON properties(cell_lat, cell_lon);
