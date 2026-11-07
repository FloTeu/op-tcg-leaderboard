-- Ensure to only have on card id at the same time. Asssume that id and language are a primary key. Language can be jp or en. Prioritize cards with language "en" and if they dont exist use the cards with language "jp"
SELECT
  t0.*,
  IFNULL(t1.image_url, t0.image_url) AS aa_image_url,
  t2.meta_format
FROM
  `cards.card` AS t0
LEFT JOIN
  `cards.card` AS t1
ON
  t0.id = t1.id
  AND t0.language = t1.language
  AND t1.aa_version = 1
LEFT JOIN
  `cards.card_release_set` AS t2
ON
  t0.release_set_id = t2.id
  AND t0.language = t2.language
WHERE
  t0.card_category = 'Leader'
  AND t0.aa_version = 0
  AND t0.language IN ('en',
    'jp')
QUALIFY
  ROW_NUMBER() OVER (PARTITION BY t0.id ORDER BY CASE WHEN t0.language = 'en' THEN 1 ELSE 2 END ) = 1
ORDER BY
  t0.id;
