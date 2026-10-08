-- CPU-only attributes; product_id is also the one-to-one link to products.id.
CREATE TABLE cpu_specs (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    socket TEXT NOT NULL,
    core_count INTEGER NOT NULL CHECK (core_count > 0),
    thread_count INTEGER NOT NULL CHECK (thread_count > 0),
    performance_core_count INTEGER CHECK (
        performance_core_count IS NULL OR performance_core_count > 0
    ),
    efficiency_core_count INTEGER CHECK (
        efficiency_core_count IS NULL OR efficiency_core_count > 0
    ),
    base_clock_mhz INTEGER NOT NULL CHECK (base_clock_mhz > 0),
    efficiency_core_base_clock_mhz INTEGER CHECK (
        efficiency_core_base_clock_mhz IS NULL OR efficiency_core_base_clock_mhz > 0
    ),
    max_clock_mhz INTEGER NOT NULL CHECK (max_clock_mhz > 0),
    max_clock_type TEXT NOT NULL CHECK (max_clock_type IN ('Max boost', 'Max turbo')),
    -- Highest PCIe generation the CPU's lanes support, such as 'PCIe 4.0'.
    max_pcie_standard TEXT NOT NULL,
    -- Highest PCIe generation of the CPU's M.2 storage lanes; can be lower than
    -- max_pcie_standard (e.g. Intel 12th/13th gen: PCIe 5.0 graphics, PCIe 4.0 M.2).
    max_storage_pcie_standard TEXT NOT NULL,
    tdp_w INTEGER NOT NULL CHECK (tdp_w > 0),
    -- SQLite stores booleans as integers: 0 = no, 1 = yes.
    stock_cooler_included INTEGER NOT NULL CHECK (stock_cooler_included IN (0, 1))
);