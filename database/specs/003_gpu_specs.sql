-- GPU-only attributes. Dimensions and power apply to the specific card model.
CREATE TABLE gpu_specs (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    vram_gb INTEGER NOT NULL CHECK (vram_gb > 0),
    tdp_w INTEGER NOT NULL CHECK (tdp_w > 0),
    length_mm REAL NOT NULL CHECK (length_mm > 0)
);