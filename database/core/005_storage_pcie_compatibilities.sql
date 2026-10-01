-- One row per PCIe compatibility string; the composite key prevents duplicates.
CREATE TABLE storage_pcie_compatibilities (
    product_id TEXT NOT NULL REFERENCES storage_specs(product_id) ON DELETE CASCADE,
    pcie_compatibility TEXT NOT NULL,
    PRIMARY KEY (product_id, pcie_compatibility)
);