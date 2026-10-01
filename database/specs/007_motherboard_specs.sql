-- Motherboard attributes used for CPU socket, case size, and memory matching.
CREATE TABLE motherboard_specs (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    socket TEXT NOT NULL,
    form_factor TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    memory_slots INTEGER NOT NULL CHECK (memory_slots > 0),
    max_memory_gb INTEGER NOT NULL CHECK (max_memory_gb > 0),
    wifi INTEGER NOT NULL CHECK (wifi IN (0, 1)) -- 0 = no, 1 = yes
);