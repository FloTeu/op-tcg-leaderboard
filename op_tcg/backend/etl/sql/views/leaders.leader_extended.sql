WITH 
-- Get all leaders and all meta formats to create complete combinations
all_leaders AS (
  SELECT DISTINCT id, meta_format as release_meta_format FROM `leaders.leader`
),
all_meta_formats AS (
  SELECT DISTINCT meta_format FROM (
    SELECT meta_format FROM `leaders.leader_elo` WHERE meta_format IS NOT NULL
    UNION DISTINCT
    SELECT meta_format FROM `leaders.tournament_winner` WHERE meta_format IS NOT NULL  
    UNION DISTINCT
    SELECT meta_format FROM `matches.leader_win_rate_aggregated` WHERE meta_format IS NOT NULL
  )
),
-- Create leader-meta_format combinations only for valid periods
leader_meta_combinations AS (
  SELECT 
    al.id as leader_id,
    al.release_meta_format,
    amf.meta_format
  FROM all_leaders al
  CROSS JOIN all_meta_formats amf
  WHERE amf.meta_format >= al.release_meta_format  -- *** KEY FIX: Only include meta formats >= release ***
),
max_values AS (
  SELECT
    lmc.meta_format,
    COALESCE(tw.meta_format_region, 'all') as meta_format_region,
    MAX(lwr.weighted_win_rate) AS max_win_rate,
    MAX(lwr.total_matches) AS max_total_matches,
    MAX(elo.elo) AS max_elo,
    MAX(COALESCE(tw.win_count, 0)) AS max_tournament_wins
  FROM leader_meta_combinations lmc
  LEFT JOIN `leaders.leader_elo` elo
    ON lmc.leader_id = elo.leader_id AND lmc.meta_format = elo.meta_format
  LEFT JOIN `leaders.tournament_winner` tw
    ON lmc.leader_id = tw.leader_id AND lmc.meta_format = tw.meta_format 
    AND (elo.only_official = tw.only_official OR elo.only_official IS NULL)
  LEFT JOIN `matches.leader_win_rate_aggregated` lwr
    ON lmc.leader_id = lwr.leader_id AND lmc.meta_format = lwr.meta_format 
    AND (elo.only_official = lwr.only_official OR elo.only_official IS NULL)
  GROUP BY lmc.meta_format, COALESCE(tw.meta_format_region, 'all')
),
normalized_values AS (
  SELECT
    l.* EXCEPT(meta_format),
    lmc.release_meta_format AS release_meta_format,  -- *** Use from combinations to ensure consistency ***
    lmc.meta_format AS meta_format,
    COALESCE(tw.win_count, 0) AS tournament_wins,
    lwr.weighted_win_rate AS win_rate,
    lwr.total_matches,
    elo.elo,
    COALESCE(lwr.only_official, elo.only_official, tw.only_official) AS only_official,
    COALESCE(tw.meta_format_region, 'all') AS meta_format_region,
    COALESCE(lwr.weighted_win_rate / NULLIF(max_values.max_win_rate, 0), 0) AS win_rate_norm,
    COALESCE(lwr.total_matches / NULLIF(max_values.max_total_matches, 0), 0) AS total_matches_norm,
    COALESCE(elo.elo / NULLIF(max_values.max_elo, 0), 0) AS elo_rating_norm,
    COALESCE(COALESCE(tw.win_count, 0) / NULLIF(max_values.max_tournament_wins, 0), 0) AS tournament_wins_norm
  FROM leader_meta_combinations lmc
  INNER JOIN `leaders.leader` l ON lmc.leader_id = l.id
  LEFT JOIN `leaders.leader_elo` elo
    ON lmc.leader_id = elo.leader_id AND lmc.meta_format = elo.meta_format
  LEFT JOIN `leaders.tournament_winner` tw
    ON lmc.leader_id = tw.leader_id AND lmc.meta_format = tw.meta_format 
    AND (elo.only_official = tw.only_official OR elo.only_official IS NULL)
  LEFT JOIN `matches.leader_win_rate_aggregated` lwr
    ON lmc.leader_id = lwr.leader_id AND lmc.meta_format = lwr.meta_format 
    AND (elo.only_official = lwr.only_official OR elo.only_official IS NULL)
  LEFT JOIN max_values
    ON lmc.meta_format = max_values.meta_format
    AND COALESCE(tw.meta_format_region, 'all') = max_values.meta_format_region
)
SELECT
  * EXCEPT(win_rate_norm, total_matches_norm, elo_rating_norm, tournament_wins_norm),
  win_rate_norm * 0.1 + total_matches_norm * 0.3 + elo_rating_norm * 0.2 + tournament_wins_norm * 0.4 AS d_score
FROM normalized_values
ORDER BY meta_format DESC, d_score DESC;
