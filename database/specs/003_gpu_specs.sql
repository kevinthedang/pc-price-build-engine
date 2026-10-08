-- GPU-only attributes. Dimensions and power apply to the specific card model.
CREATE TABLE gpu_specs (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    vram_gb INTEGER NOT NULL CHECK (vram_gb > 0),
    tdp_w INTEGER NOT NULL CHECK (tdp_w > 0),
    length_mm REAL NOT NULL CHECK (length_mm > 0),
    game_clock_mhz INTEGER CHECK (game_clock_mhz IS NULL OR game_clock_mhz > 0),
    boost_clock_mhz INTEGER CHECK (boost_clock_mhz IS NULL OR boost_clock_mhz > 0),
    oc_game_clock_mhz INTEGER CHECK (oc_game_clock_mhz IS NULL OR oc_game_clock_mhz > 0),
    oc_boost_clock_mhz INTEGER CHECK (oc_boost_clock_mhz IS NULL OR oc_boost_clock_mhz > 0),
    pcie_standard TEXT,
    recommended_psu_w INTEGER CHECK (
        recommended_psu_w IS NULL OR recommended_psu_w > 0
    ),
    pcie_slot_width REAL CHECK (pcie_slot_width IS NULL OR pcie_slot_width > 0)
);