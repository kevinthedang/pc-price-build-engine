-- Cooler dimensions are nullable when they do not apply: air coolers use
-- height_mm; AIO coolers use the radiator and pump measurements.
CREATE TABLE cooler_specs (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    cooler_type TEXT NOT NULL CHECK (cooler_type IN ('air', 'aio')),
    height_mm REAL CHECK (height_mm IS NULL OR height_mm > 0),
    -- Advertised cooling estimate; this is not a standardized guarantee.
    max_tdp_w INTEGER NOT NULL CHECK (max_tdp_w > 0),
    radiator_size_mm INTEGER CHECK (radiator_size_mm IS NULL OR radiator_size_mm > 0),
    radiator_thickness_mm REAL CHECK (radiator_thickness_mm IS NULL OR radiator_thickness_mm > 0),
    pump_height_mm REAL CHECK (pump_height_mm IS NULL OR pump_height_mm > 0)
);