-- Manufacturer-rated maximum memory speed per supported memory type for a CPU.
CREATE TABLE cpu_memory_speeds (
    memory_speed_id INTEGER PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL CHECK (length(trim(memory_type)) > 0),
    max_speed_mhz INTEGER NOT NULL CHECK (max_speed_mhz > 0),
    UNIQUE (product_id, memory_type)
);
