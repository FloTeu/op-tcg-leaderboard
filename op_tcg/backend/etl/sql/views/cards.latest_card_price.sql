WITH LatestPrices AS (
    SELECT
        card_id,
        language,
        aa_version,
        currency,
        price,
        create_timestamp,
        ROW_NUMBER() OVER (PARTITION BY card_id, language, aa_version, currency ORDER BY create_timestamp DESC) AS row_num
    FROM
        `cards.card_price`
),
LatestEuroPrices AS (
    SELECT
        card_id,
        language,
        aa_version,
        create_timestamp,
        price AS latest_eur_price
    FROM
        LatestPrices
    WHERE
        currency = 'eur' AND row_num = 1
),
LatestUsdPrices AS (
    SELECT
        card_id,
        language,
        aa_version,
        price AS latest_usd_price
    FROM
        LatestPrices
    WHERE
        currency = 'usd' AND row_num = 1
)
SELECT
    c.* except(create_timestamp),
    CASE WHEN le.create_timestamp IS NOT NULL THEN le.create_timestamp else c.create_timestamp END AS create_timestamp,
    le.latest_eur_price,
    lu.latest_usd_price
FROM
    `cards.card` c
LEFT JOIN
    LatestEuroPrices le
ON
    c.id = le.card_id AND c.language = le.language AND c.aa_version = le.aa_version
LEFT JOIN
    LatestUsdPrices lu
ON
    c.id = lu.card_id AND c.language = lu.language AND c.aa_version = lu.aa_version

