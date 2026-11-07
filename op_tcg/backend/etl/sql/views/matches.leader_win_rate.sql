WITH MatchResultsAll AS (
  SELECT
    meta_format,
    leader_id,
    opponent_id,
    SUM(CASE WHEN result = 2 THEN 1 ELSE 0 END) AS wins,
    COUNT(*) AS total_matches
  FROM
    `matches.match`
  WHERE result != 1 -- ignore draw rounds
  GROUP BY
    leader_id,
    opponent_id,
    meta_format
),
MatchResultsOnlyOfficial AS (
  SELECT
    meta_format,
    leader_id,
    opponent_id,
    SUM(CASE WHEN result = 2 THEN 1 ELSE 0 END) AS wins,
    COUNT(*) AS total_matches
  FROM
    `matches.match`
  WHERE
    official and result != 1 -- ignore draw rounds
  GROUP BY
    leader_id,
    opponent_id,
    meta_format
)
-- Query without the WHERE clause
SELECT
  meta_format,
  leader_id,
  opponent_id,
  IFNULL(SAFE_DIVIDE(wins, total_matches), 0) AS win_rate,
  total_matches,
  False as only_official
FROM
  MatchResultsAll

UNION ALL

-- Query with the WHERE clause
SELECT
  meta_format,
  leader_id,
  opponent_id,
  IFNULL(SAFE_DIVIDE(wins, total_matches), 0) AS win_rate,
  total_matches,
  TRUE as only_official
FROM
  MatchResultsOnlyOfficial

ORDER BY
  meta_format,
  leader_id,
  opponent_id;

