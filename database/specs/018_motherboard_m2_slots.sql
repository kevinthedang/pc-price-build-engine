-- M.2 storage slots on a motherboard; lane_source shows whether the slot's lanes
-- come from the CPU (so the CPU's storage PCIe limit applies) or the chipset.
CREATE TABLE motherboard_m2_slots (
    m2_slot_id INTEGER PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    slot_name TEXT NOT NULL CHECK (length(trim(slot_name)) > 0),
    pcie_standard TEXT NOT NULL CHECK (length(trim(pcie_standard)) > 0),
    lane_source TEXT NOT NULL CHECK (lane_source IN ('CPU', 'Chipset')),
    UNIQUE (product_id, slot_name)
);
