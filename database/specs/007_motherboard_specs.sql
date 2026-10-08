-- Motherboard attributes used for CPU socket, case size, memory, and PCIe matching.
CREATE TABLE motherboard_specs (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    socket TEXT NOT NULL,
    form_factor TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    memory_slots INTEGER NOT NULL CHECK (memory_slots > 0),
    max_memory_gb INTEGER NOT NULL CHECK (max_memory_gb > 0),
    wifi INTEGER NOT NULL CHECK (wifi IN (0, 1)), -- 0 = no, 1 = yes
    sata_ports INTEGER NOT NULL CHECK (sata_ports >= 0),
    -- PCIe generation of the primary (CPU-connected) x16 graphics slot.
    pcie_x16_standard TEXT NOT NULL
);