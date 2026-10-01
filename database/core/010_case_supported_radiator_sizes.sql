-- One row per radiator size supported by a case, in millimeters.
CREATE TABLE case_supported_radiator_sizes (
    product_id TEXT NOT NULL REFERENCES case_specs(product_id) ON DELETE CASCADE,
    radiator_size_mm INTEGER NOT NULL CHECK (radiator_size_mm > 0),
    PRIMARY KEY (product_id, radiator_size_mm)
);