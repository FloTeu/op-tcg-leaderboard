WITH LeaderPlacings AS (
  SELECT
    tournament_id,
    leader_id,
    ARRAY_AGG(COALESCE(placing, -1)) AS placings
  FROM
    `matches.tournament_standing`
  WHERE
    leader_id IS NOT NULL
  GROUP BY
    tournament_id,
    leader_id
),

AggregatedLeaderPlacings AS (
  SELECT
    tournament_id,
    CONCAT('{', STRING_AGG(
      CONCAT('"', leader_id, '": ', TO_JSON_STRING(placings))
    ), '}') AS leader_ids_placing
  FROM
    LeaderPlacings
  GROUP BY
    tournament_id
),

RankedOpTopDeckDecklists AS (
  SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY tournament_id ORDER BY tournament_id DESC) AS rn
  FROM
    `matches.op_top_deck_decklist`
)

SELECT
  t.* except(meta_format_region),
  COALESCE(t.meta_format_region, 'west') AS meta_format_region,
  COALESCE(alp.leader_ids_placing, '{}') AS leader_ids_placings,
  opd.host,
  opd.country
FROM
  `matches.tournament` t
LEFT JOIN
  AggregatedLeaderPlacings alp
ON
  t.id = alp.tournament_id
LEFT JOIN
  RankedOpTopDeckDecklists opd
ON
  t.id = opd.tournament_id
WHERE
  opd.rn = 1 OR opd.rn IS NULL

