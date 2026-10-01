-- Storage capacity and media/interface category for one product.
CREATE TABLE storage_specs (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    storage_type TEXT NOT NULL,
    size_gb INTEGER NOT NULL CHECK (size_gb > 0)
);