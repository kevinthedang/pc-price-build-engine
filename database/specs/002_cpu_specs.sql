-- CPU-only attributes; product_id is also the one-to-one link to products.id.
CREATE TABLE cpu_specs (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    socket TEXT NOT NULL,
    tdp_w INTEGER NOT NULL CHECK (tdp_w > 0),
    -- SQLite stores booleans as integers: 0 = no, 1 = yes.
    stock_cooler_included INTEGER NOT NULL CHECK (stock_cooler_included IN (0, 1))
);