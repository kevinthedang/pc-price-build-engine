-- A product can have many retailer offers. Prices and shipping use integer cents.
CREATE TABLE offers (
    offer_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    retailer_id INTEGER NOT NULL REFERENCES retailers(id),
    retailer_product_id TEXT,
    url TEXT,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    shipping_cents INTEGER NOT NULL DEFAULT 0 CHECK (shipping_cents >= 0),
    currency TEXT NOT NULL DEFAULT 'USD' CHECK (length(currency) = 3),
    availability TEXT NOT NULL,
    condition TEXT NOT NULL,
    seller TEXT,
    checked_at TEXT NOT NULL -- ISO-8601 timestamp for when this price was checked
);

-- Speed up product price comparisons and finding stale/recent observations.
CREATE INDEX offers_product_price_idx
    ON offers(product_id, price_cents, shipping_cents);
CREATE INDEX offers_checked_at_idx
    ON offers(checked_at);