-- Memory kit specifications. capacity_gb is per module, not the kit total.
CREATE TABLE memory_specs (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL,
    capacity_gb INTEGER NOT NULL CHECK (capacity_gb > 0),
    modules INTEGER NOT NULL CHECK (modules > 0),
    speed_mhz INTEGER NOT NULL CHECK (speed_mhz > 0)
);