-- One row per CPU socket supported by a cooler.
CREATE TABLE cooler_supported_sockets (
    product_id TEXT NOT NULL REFERENCES cooler_specs(product_id) ON DELETE CASCADE,
    socket TEXT NOT NULL,
    PRIMARY KEY (product_id, socket)
);