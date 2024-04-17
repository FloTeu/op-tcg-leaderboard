import pandas as pd

from op_tcg.backend.models.matches import MatchResult, BQLeaderElos, BQLeaderElo


class EloCreator:
    leader_id2elo: dict[str, int]

    def __init__(self, df_all_matches: pd.DataFrame):
        self.df_all_matches = df_all_matches
        self.leader_id2elo = {leader_id: 1000 for leader_id in df_all_matches.leader_id.unique()}
        self.start_date = df_all_matches.sort_values("timestamp", ascending=True).iloc[0].timestamp.date()
        self.end_date = df_all_matches.sort_values("timestamp", ascending=False).iloc[0].timestamp.date()
        self.only_official = len(df_all_matches.query("official != True")) == 0
        self.meta_format = df_all_matches.sort_values("timestamp", ascending=False).iloc[0].meta_format

    def calculate_elo_ratings(self):
        for i, df_row in self.df_all_matches.sort_values("timestamp", ascending=True).iterrows():
            current_leader_elo = self.leader_id2elo[df_row.leader_id]
            current_opponent_elo = self.leader_id2elo[df_row.opponent_id]
            self.leader_id2elo[df_row.leader_id] = calculate_new_elo(current_leader_elo, current_opponent_elo,
                                                                     df_row.result, k_factor=32)

    def to_bq_leader_elos(self) -> BQLeaderElos:
        leader_elos: list[BQLeaderElo] = []
        for leader_id, elo in self.leader_id2elo.items():
            leader_elos.append(BQLeaderElo(
                leader_id=leader_id,
                elo=elo,
                only_official=self.only_official,
                meta_format=self.meta_format,
                start_date=self.start_date,
                end_date=self.end_date
            ))
        return BQLeaderElos(elo_ratings=leader_elos)


def calculate_new_elo(current_elo: int, opponent_elo: int, result: MatchResult, k_factor=32):
    """
    Calculate the new Elo rating for a player based on the current rating,
    opponent's rating, and the match result.

    :param current_elo: int - The current Elo rating of the player
    :param opponent_elo: int - The Elo rating of the opponent
    :param result: MatchResult - The result of the match (0 for loss, 1 for draw, 2 for win)
    :param k_factor: int - The K-factor used in the Elo rating (default is 32)
    :return: int - The new Elo rating of the player
    """
    # Convert the result to the expected score format (0 for loss, 0.5 for draw, 1 for win)
    actual_score = result / 2

    # Calculate the expected score
    expected_score = 1 / (1 + 10 ** ((opponent_elo - current_elo) / 400))

    # Calculate the new Elo rating
    new_elo = current_elo + k_factor * (actual_score - expected_score)

    return round(new_elo)
