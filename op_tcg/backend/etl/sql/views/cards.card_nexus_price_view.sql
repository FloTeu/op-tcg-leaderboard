-- Unified CardNexus price history joined with the product mapping, shaped like our own card/price columns.
-- Exposes the full daily history; consumers wanting the current price filter/QUALIFY on MAX(date) themselves.
SELECT
    m.card_id,
    m.language,
    m.aa_version,
    h.marketplace,
    h.finish,
    h.date,
    h.currency,
    h.low,
    h.mid,
    h.high,
    h.market_value,
    'cardnexus' AS source
FROM `cardnexus_raw.card_nexus_price` h
JOIN `cards.card_nexus_card_product_mapping` m
    ON h.product_id = m.product_id
WHERE m.matched
