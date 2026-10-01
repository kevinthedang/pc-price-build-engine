-- Shared identity for every component. Specs tables and offers refer to this ID.
CREATE TABLE products (
    id TEXT PRIMARY KEY,
    -- Intended to match the specs table; cross-table matching is not enforced yet.
    product_type TEXT NOT NULL CHECK (
        product_type IN (
            'cpu', 'gpu', 'storage', 'memory', 'motherboard', 'case', 'cooler', 'psu'
        )
    ),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0)
);