WITH meta_combinations AS (
  SELECT DISTINCT
    meta_format,
    only_official,
    meta_format_region
  FROM (
    SELECT t.meta_format, False AS only_official, 'all' AS meta_format_region FROM `matches.tournament` t
    UNION ALL
    SELECT t.meta_format, True AS only_official, 'all' AS meta_format_region FROM `matches.tournament` t WHERE t.official
    UNION ALL
    SELECT t.meta_format, True AS only_official, 'west' AS meta_format_region FROM `matches.tournament` t WHERE t.official AND COALESCE(t.meta_format_region, 'west') = 'west'
    UNION ALL
    SELECT t.meta_format, True AS only_official, 'asia' AS meta_format_region FROM `matches.tournament` t WHERE t.official AND t.meta_format_region = 'asia'
    UNION ALL
    SELECT t.meta_format, False AS only_official, 'west' AS meta_format_region FROM `matches.tournament` t WHERE COALESCE(t.meta_format_region, 'west') = 'west'
    UNION ALL
    SELECT t.meta_format, False AS only_official, 'asia' AS meta_format_region FROM `matches.tournament` t WHERE t.meta_format_region = 'asia'
  )
),
leader_combinations AS (
  SELECT
    l.id AS leader_id,
    mc.meta_format,
    mc.only_official,
    mc.meta_format_region
  FROM `leaders.leader` l
  CROSS JOIN meta_combinations mc
)
SELECT
  lc.meta_format,
  lc.leader_id,
  COALESCE(SUM(CASE WHEN t1.placing = 1 THEN 1 ELSE 0 END), 0) AS win_count,
  lc.only_official,
  lc.meta_format_region,
FROM leader_combinations lc
LEFT JOIN `matches.tournament` t2 ON
    lc.meta_format = t2.meta_format
    AND (lc.only_official = False OR lc.only_official = t2.official)
    AND (
      (lc.meta_format_region = 'all') OR
      -- expect missing meta_format_region to be "west"
      (lc.meta_format_region = 'west' AND COALESCE(t2.meta_format_region, 'west') = 'west') OR
      (lc.meta_format_region = 'asia' AND t2.meta_format_region = 'asia')
    )
LEFT JOIN `matches.tournament_standing` t1 ON lc.leader_id = t1.leader_id
    AND t1.tournament_id = t2.id
GROUP BY lc.meta_format, lc.leader_id, lc.only_official, lc.meta_format_region
ORDER BY lc.meta_format DESC, win_count DESC;
