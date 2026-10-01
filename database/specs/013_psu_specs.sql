-- PSU-specific attributes. ID and name are stored once in products.
CREATE TABLE psu_specs (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    wattage INTEGER NOT NULL CHECK (wattage > 0),
    efficiency TEXT NOT NULL
);