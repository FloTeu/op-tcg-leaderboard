from datetime import datetime, timedelta
from uuid import uuid4

import scrapy
import requests
import json

from google.cloud import bigquery
from pydantic import BaseModel

from op_tcg.backend.etl.transform import meta_format2release_datetime
from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.tournaments import Tournament, TournamentStanding
from op_tcg.backend.models.matches import Match, MatchResult


class LimitlessTournamentSpider(scrapy.Spider):
    name = "limitless_tournaments"

    meta_formats: list[MetaFormat]
    api_token: str

    def meta_format2limitless_formats(self, meta_format: MetaFormat) -> list[str]:
        response = requests.get(f"https://play.limitlesstcg.com/api/games?key={self.api_token}")
        limitless_games: list[dict[str, str]] = json.loads(response.content)

        optcg_formats: dict[str, str] = \
            [limitless_game for limitless_game in limitless_games if "OP" == limitless_game["id"]][0]["formats"]
        # TODO: Filter by meta_formats
        return list(optcg_formats.keys())

    def start_requests(self):
        self.bq_client = bigquery.Client(location="europe-west3")
        # meta_formats: list[MetaFormat] = self.meta_formats if self.meta_formats else [MetaFormat.OP01]
        # meta_format2limitless_formats_dict: dict[str, list[str]] = {}
        # for meta_format in meta_formats:
        #     meta_format2limitless_formats_dict[meta_format] = self.meta_format2limitless_formats(meta_format)

        # for meta_format, limitless_formats in meta_format2limitless_formats_dict.items():
        #     for limitless_format in limitless_formats:
        url = f"https://play.limitlesstcg.com/api/tournaments?game=OP&limit=2&key={self.api_token}"
        yield scrapy.Request(url=url, callback=self.parse_tournaments)

    def parse_tournaments(self, response):
        json_res: list[dict[str, str]] = json.loads(response.body)
        for tournament in json_res:
            # todo: decide if its official
            official = True
            url = f"https://play.limitlesstcg.com/api/tournaments/{tournament['id']}/standings?key={self.api_token}"
            yield scrapy.Request(url=url, callback=self.parse_tournament_standings,
                                 meta={"official": official, **tournament})

    def get_meta_format(self, all_decklists: list[dict[str, int]], tournament_date: datetime) -> MetaFormat:
        for meta_format in sorted(MetaFormat.to_list(), reverse=True):
            for decklists in all_decklists:
                if any(card_id.split("-")[0] == meta_format for card_id in  decklists.keys()):
                    return meta_format
        for meta_format in sorted(MetaFormat.to_list(), reverse=True):
            if tournament_date > meta_format2release_datetime(meta_format):
                return meta_format
        raise ValueError("tournament could not be matched to meta_format")

    def parse_tournament_standings(self, response):
        json_res: list[dict[str, str]] = json.loads(response.body)
        player_id2leader_id: dict[str, str] = {}
        all_decklists: list[dict[str, int]] = []
        for standing in json_res:
            decklist = standing["decklist"]
            leader_id = None
            if decklist:
                leader_id = f'{decklist["leader"]["set"]}-{decklist["leader"]["number"]}'
                # leader + deck
                decklist = {leader_id: 1, **{f'{card["set"]}-{card["number"]}': card["count"] for card in
                                             decklist["character"] + decklist["event"] + decklist["stage"]}}
                assert sum(decklist.values()) == 51, "Sum of card in deck should be 51"
                all_decklists.append(decklist)

            tournament_standing = TournamentStanding(tournament_id=response.meta["id"], leader_id=leader_id,
                                                     decklist=decklist,
                                                     **{k: v for k, v in standing.items() if k not in ["decklist"]})
            player_id2leader_id[standing["player"]] = leader_id
            yield tournament_standing

        meta_format = self.get_meta_format(all_decklists,
            tournament_date = datetime.strptime(response.meta["date"], "%Y-%m-%dT%H:%M:%S.%fZ"))
        url = f"https://play.limitlesstcg.com/api/tournaments/{response.meta['id']}/pairings?key={self.api_token}"
        # only add matches, if all players have a leader information
        if not any(leader_id == None for leader_id in player_id2leader_id.values()):
            yield scrapy.Request(url=url, callback=self.parse_tournament_pairings,
                                 meta={"player_id2leader_id": player_id2leader_id, "meta_format": meta_format,
                                       **response.meta})

        url = f"https://play.limitlesstcg.com/api/tournaments/{response.meta['id']}/details?key={self.api_token}"
        yield scrapy.Request(url=url, callback=self.parse_tournament,
                             meta={"meta_format": meta_format, "official": response.meta["official"]})

    def parse_tournament_pairings(self, response):
        json_res: list[dict[str, str]] = json.loads(response.body)

        class MatchPairingResult(BaseModel):
            id: str
            result: MatchResult
            player_id: str
            opponent_player_id: str
            is_reverse: bool
            match_timestamp: datetime

        for pairing in json_res:
            id = uuid4().hex  # define new unique match id
            winner = pairing["winner"]
            datetime_obj = datetime.strptime(response.meta["date"], "%Y-%m-%dT%H:%M:%S.%fZ")

            # Assumes 30 minutes for each match
            match_timestamp = datetime_obj + timedelta(minutes=30 * pairing["round"])
            # list of 2 matches (one match + one reverse match)
            match_results: list[MatchPairingResult] = []
            if str(winner) in ["0", "-1"]:
                match_results.append(MatchPairingResult(id=id, result=MatchResult.DRAW, player_id=pairing["player1"],
                                                        opponent_player_id=pairing["player2"], is_reverse=False,
                                                        match_timestamp=match_timestamp))
                match_results.append(MatchPairingResult(id=id, result=MatchResult.DRAW, player_id=pairing["player2"],
                                                        opponent_player_id=pairing["player1"], is_reverse=True,
                                                        match_timestamp=match_timestamp))
            else:
                player_id = pairing["winner"]
                opponent_player_id = pairing["player1"] if player_id != pairing["player1"] else pairing["player2"]
                match_results.append(MatchPairingResult(id=id, result=MatchResult.WIN, player_id=player_id,
                                                        opponent_player_id=opponent_player_id, is_reverse=False,
                                                        match_timestamp=match_timestamp))
                match_results.append(MatchPairingResult(id=id, result=MatchResult.LOSE, player_id=opponent_player_id,
                                                        opponent_player_id=player_id, is_reverse=True,
                                                        match_timestamp=match_timestamp))
            assert len(match_results) == 2

            for match_result in match_results:
                match = Match(
                    leader_id=response.meta["player_id2leader_id"][match_result.player_id],
                    opponent_id=response.meta["player_id2leader_id"][match_result.opponent_player_id],
                    meta_format=response.meta["meta_format"],
                    tournament_id=response.meta["id"],
                    source=DataSource.LIMITLESS,
                    official=response.meta["official"],
                    **{**match_result.model_dump(), **pairing}
                )
                yield match

    def parse_tournament(self, response):
        json_res: dict[str, str] = json.loads(response.body)
        tournament = Tournament(official=response.meta["official"], source=DataSource.LIMITLESS,
                                meta_format=response.meta["meta_format"],
                                **json_res)
        yield tournament
