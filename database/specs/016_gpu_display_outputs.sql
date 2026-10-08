-- Display connectors for a specific graphics card model.
CREATE TABLE gpu_display_outputs (
    output_id INTEGER PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    output_type TEXT NOT NULL CHECK (length(trim(output_type)) > 0),
    version TEXT,
    output_count INTEGER NOT NULL CHECK (output_count > 0)
);
