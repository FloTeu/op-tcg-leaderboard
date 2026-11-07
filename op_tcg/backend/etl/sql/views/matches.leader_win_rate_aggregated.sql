SELECT
  leader_id,
  meta_format,
  only_official,
  SUM(win_rate * total_matches) / SUM(total_matches) AS weighted_win_rate,
  SUM(total_matches) AS total_matches
FROM
  `matches.leader_win_rate`
GROUP BY
  leader_id,
  meta_format,
  only_official
