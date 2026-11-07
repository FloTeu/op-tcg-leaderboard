-- CardNexus sealed-product price history, shaped like our SealedProductPrice table. Not wired into the app yet.
SELECT
    p.product_id,
    p.name,
    p.product_category,
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
JOIN `cardnexus_raw.card_nexus_sealed_product` p
    ON h.product_id = p.product_id
