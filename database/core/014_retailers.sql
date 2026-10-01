-- Canonical retailer names so offers can reference a retailer by ID.
CREATE TABLE retailers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0)
);