-- CardNexus's own sealed-product catalog (booster boxes, cases, starter decks, ...), standalone (not joined to
-- CardNexusSealedProductMapping), shaped like our SealedProduct table. Not wired into the app yet.
SELECT
    product_id,
    name,
    product_category,
    expansion_id,
    expansion_slug,
    image_url,
    create_timestamp
FROM `cardnexus_raw.card_nexus_sealed_product`
