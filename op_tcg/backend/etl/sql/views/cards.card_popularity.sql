WITH DecklistColors AS (
    SELECT
        ts.tournament_id,
        COALESCE(d.decklist, ts.decklist) AS decklist,
        l.colors AS leader_colors,
        l.id, l.language,
        t.meta_format
    FROM
        matches.tournament_standing ts
    JOIN
        matches.tournament t
    ON
        ts.tournament_id = t.id
    LEFT JOIN
        leaders.leader l
    ON
        ts.leader_id = l.id
    LEFT JOIN
        matches.decklist d
    ON
        ts.decklist_id = d.id
    where COALESCE(d.decklist, ts.decklist) is not null
),
ParsedDecklists AS (
    SELECT
        tournament_id,
        SPLIT(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(decklist, r"^\{|\}$", ""), r"', '", "','"), r" '", "'"), ",") AS parsed_decklist,
        leader_colors,
        meta_format
    FROM
        DecklistColors
),
CardInstances AS (
    SELECT
        TRIM(SPLIT(card_entry, ":")[OFFSET(0)], "'") AS card_id,
        pd.meta_format,
        leader_color,
        COUNT(*) AS card_count
    FROM
        ParsedDecklists pd,
        UNNEST(pd.parsed_decklist) AS card_entry,
        UNNEST(pd.leader_colors) AS leader_color
    GROUP BY
        card_id, pd.meta_format, leader_color
),
ColorDeckCounts AS (
    SELECT
        pd.meta_format,
        leader_color,
        COUNT(pd.tournament_id) AS total_decks
    FROM
        ParsedDecklists pd,
        UNNEST(pd.leader_colors) AS leader_color
    GROUP BY
        pd.meta_format, leader_color
)

SELECT
    ci.card_id,
    ci.meta_format,
    ci.leader_color AS color,
    IFNULL(ci.card_count / cdc.total_decks, 0) AS popularity
FROM
    CardInstances ci
LEFT JOIN
    ColorDeckCounts cdc
ON
    ci.meta_format = cdc.meta_format
    AND ci.leader_color = cdc.leader_color
order by meta_format, popularity desc
