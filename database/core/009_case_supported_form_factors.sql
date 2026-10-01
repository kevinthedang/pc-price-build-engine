-- One row per motherboard form factor supported by a case.
CREATE TABLE case_supported_form_factors (
    product_id TEXT NOT NULL REFERENCES case_specs(product_id) ON DELETE CASCADE,
    form_factor TEXT NOT NULL,
    PRIMARY KEY (product_id, form_factor)
);