-- Storage capacity and media/interface category for one product.
CREATE TABLE storage_specs (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    storage_type TEXT NOT NULL,
    -- Physical form factor, such as 'M.2 2280', '2.5-inch', or '3.5-inch'.
    form_factor TEXT NOT NULL CHECK (length(trim(form_factor)) > 0),
    size_gb INTEGER NOT NULL CHECK (size_gb > 0)
);