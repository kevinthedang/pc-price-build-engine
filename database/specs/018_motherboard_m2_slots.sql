-- M.2 storage slots on a motherboard; lane_source shows whether the slot's lanes
-- come from the CPU (so the CPU's storage PCIe limit applies) or the chipset.
CREATE TABLE motherboard_m2_slots (
    m2_slot_id INTEGER PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    slot_name TEXT NOT NULL CHECK (length(trim(slot_name)) > 0),
    pcie_standard TEXT NOT NULL CHECK (length(trim(pcie_standard)) > 0),
    lane_source TEXT NOT NULL CHECK (lane_source IN ('CPU', 'Chipset')),
    -- Whether the slot accepts M.2 SATA drives (0 = PCIe only, 1 = PCIe or SATA).
    supports_sata INTEGER NOT NULL CHECK (supports_sata IN (0, 1)),
    -- SATA ports that become unavailable while the slot holds an M.2 SATA drive.
    sata_ports_disabled_in_sata_mode INTEGER NOT NULL DEFAULT 0 CHECK (
        sata_ports_disabled_in_sata_mode >= 0
        AND (supports_sata = 1 OR sata_ports_disabled_in_sata_mode = 0)
    ),
    UNIQUE (product_id, slot_name)
);
