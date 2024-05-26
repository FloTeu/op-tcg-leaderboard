from uuid import uuid4

import pandas as pd

from op_tcg.backend.models.matches import MatchResult, BQLeaderElos, LeaderElo


class EloCreator:
    leader_id2elo: dict[str, int]

    def __init__(self, df_all_matches: pd.DataFrame, only_official: bool | None = None):
        self.df_all_matches = df_all_matches
        self.leader_id2elo = {leader_id: 1000 for leader_id in df_all_matches.leader_id.unique()}
        self.start_date = df_all_matches.sort_values("match_timestamp", ascending=True).iloc[0].match_timestamp.date()
        self.end_date = df_all_matches.sort_values("match_timestamp", ascending=False).iloc[0].match_timestamp.date()
        self.only_official = only_official if only_official is not None else len(df_all_matches.query("official != True")) == 0
        self.meta_format = df_all_matches.sort_values("match_timestamp", ascending=False).iloc[0].meta_format

    def get_k_factor(self, leader_elo) -> int:
        k_factor = 32
        if leader_elo >= 3000:
            k_factor = 5
        # ranges of FIDE
        elif leader_elo >= 2400:
            k_factor = 10
        elif leader_elo >= 1500:
            k_factor = 20
        return k_factor

    def calculate_elo_ratings(self):
        match_timestamps = self.df_all_matches.sort_values("match_timestamp", ascending=True).match_timestamp.unique().tolist()
        df_all_matches = self.df_all_matches.set_index('match_timestamp')
        for match_timestamp in match_timestamps:
            saka_elo_change = []
            leader_id2elo_change: dict[str, int] = {lid: 0 for lid in self.leader_id2elo.keys()}
            df_matches_at_same_time = df_all_matches.loc[match_timestamp]

            def add_elo_change_of_match(df_match) -> None:
                leader_id2elo_change_match: dict[str, int] = {lid: 0 for lid in self.leader_id2elo.keys()}
                for i, match_data_row in df_match.iterrows():
                    # include dynamic elo change as otherwise high elo leader penalty is too high
                    leader_elo = self.leader_id2elo[match_data_row.leader_id] + leader_id2elo_change[
                        match_data_row.leader_id]
                    opponent_elo = self.leader_id2elo[match_data_row.opponent_id] + leader_id2elo_change[
                        match_data_row.opponent_id]
                    k_factor = self.get_k_factor(leader_elo)
                    new_elo = calculate_new_elo(leader_elo,
                                                opponent_elo,
                                                match_data_row.result,
                                                k_factor=k_factor)

                    # in case of mirror match, leader elo change should not be overwritten, but added
                    leader_id2elo_change_match[match_data_row.leader_id] += (new_elo - leader_elo)

                for leader_id, elo_change in leader_id2elo_change_match.items():
                    if elo_change != 0:
                        if leader_id == "OP05-041":
                            saka_elo_change.append(f"{self.leader_id2elo[match_data_row.leader_id] + leader_id2elo_change[leader_id]} | {elo_change}")
                        leader_id2elo_change[leader_id] += elo_change

            # random shuffle with id (order has a strong impact in elo)
            id2random = {id: uuid4().hex for id in df_matches_at_same_time.id.unique().tolist()}
            df_matches_at_same_time["id_random"] = df_matches_at_same_time["id"].map(lambda x: id2random[x])
            # apply elo change for each match
            df_matches_at_same_time.groupby("id_random").apply(add_elo_change_of_match)

            for leader_id, elo_change in leader_id2elo_change.items():
                self.leader_id2elo[leader_id] = self.leader_id2elo[leader_id] + elo_change
        print("Elo calculation completed")


    def to_bq_leader_elos(self) -> BQLeaderElos:
        leader_elos: list[LeaderElo] = []
        for leader_id, elo in self.leader_id2elo.items():
            leader_elos.append(LeaderElo(
                leader_id=leader_id,
                elo=elo,
                only_official=self.only_official,
                meta_format=self.meta_format,
                start_date=self.start_date,
                end_date=self.end_date
            ))
        return BQLeaderElos(elo_ratings=leader_elos)


def calculate_new_elo(current_elo: int, opponent_elo: int, result: MatchResult, k_factor=32) -> int:
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

    return int(round(new_elo))
