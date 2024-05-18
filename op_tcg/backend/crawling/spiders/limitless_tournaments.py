from datetime import datetime, timedelta
from uuid import uuid4

import scrapy
import requests
import json
from pathlib import Path
from bs4 import BeautifulSoup
from pydantic import BaseModel

from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.input import LimitlessMatch, LimitlessLeaderMetaDoc, MetaFormat
from op_tcg.backend.etl.extract import read_json_files
from op_tcg.backend.models.tournaments import Tournament, TournamentStandings
from op_tcg.backend.models.matches import Match, MatchResult


class LimitlessTournamentSpider(scrapy.Spider):
    name = "limitless_tournaments"

    meta_formats: list[MetaFormat]
    api_token: str

    def meta_format2limitless_formats(self, meta_format: MetaFormat) -> list[str]:
        limitless_games = requests.get(f"https://play.limitlesstcg.com/api/games?key={self.api_token}")
        optcg_formats: dict[str, str] = \
        [limitless_game for limitless_game in limitless_games if "OPTCG" == limitless_game["id"]][0]["formats"]
        # TODO: Filter by meta_formats
        return list(optcg_formats.keys())

    def start_requests(self):
        meta_formats: list[MetaFormat] = self.meta_formats if self.meta_formats else [MetaFormat.OP01]
        meta_format2limitless_formats_dict: dict[str, list[str]] = {}
        for meta_format in meta_formats:
            meta_format2limitless_formats_dict[meta_format] = self.meta_format2limitless_formats(meta_format)

        for meta_format, limitless_formats in meta_format2limitless_formats_dict.items():
            for limitless_format in limitless_formats:
                url = f"https://play.limitlesstcg.com/api/tournaments?game=OP&format={limitless_format}&key={self.api_token}"
                yield scrapy.Request(url=url, callback=self.parse_tournaments, meta={"meta_format": meta_format})

    def parse_tournaments(self, response):
        json_res: list[dict[str, str]] = json.loads(response.body)
        meta_format = response.meta.get('meta_format')
        for tournament in json_res:
            # todo: decide if its official
            official = True
            url = f"https://play.limitlesstcg.com/api/tournaments/{tournament['id']}/details?key={self.api_token}"
            yield scrapy.Request(url=url, callback=self.parse_tournament, meta={"meta_format": meta_format, "official": official})
            url = f"https://play.limitlesstcg.com/api/tournaments/{tournament['id']}/standings?key={self.api_token}"
            yield scrapy.Request(url=url, callback=self.parse_tournament_standings, meta={"meta_format": meta_format, "official": official, **tournament})

    def parse_tournament(self, response):
        json_res: dict[str, str] = json.loads(response.body)
        tournament = Tournament(official=response.meta["official"], source=DataSource.LIMITLESS, meta_format=response.meta["meta_format"],
                                **json_res)
        yield tournament

    def parse_tournament_standings(self, response):
        json_res: list[dict[str, str]] = json.loads(response.body)
        player_id2leader_id: dict[str, str] = {}
        for standing in json_res:
            # TODO check if this is true for leader id
            decklist = standing["decklist"]
            leader_id = list(standing.get("decklist").keys())[0]
            tournament_standing = TournamentStandings(tournament_id=response.meta["id"], leader_id=leader_id,
                                                      decklist=decklist, **standing)
            player_id2leader_id[standing["player"]] = leader_id
            yield tournament_standing

        url = f"https://play.limitlesstcg.com/api/tournaments/{response.meta['id']}/pairings?key={self.api_token}"
        yield scrapy.Request(url=url, callback=self.parse_tournament_pairings,
                             meta={"player_id2leader_id": player_id2leader_id,  **response.meta})

    def parse_tournament_pairings(self, response):
        json_res: list[dict[str, str]] = json.loads(response.body)
        # TODO
        """
        [
            {
                "round": 1,
                "phase": 1,
                "table": 1,
                "winner": "shoji300",
                "player1": "hedilily",
                "player2": "shoji300"
            },
            ...
            {
                "phase": 2,
                "round": 12,
                "match": "T2-1",
                "winner": "espel",
                "player1": "harun",
                "player2": "espel"
            }
        ]
        
        class Match(BQTableBaseModel):
                id: str = Field(description="Unique id of single match. One match contains 2 rows, including one reverse match", primary_key=True)
                leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
                opponent_id: str = Field(description="The op tcg opponent id e.g. OP03-099")
                result: MatchResult = Field(description="Result of the match. Can be win, lose or draw")
                meta_format: MetaFormat = Field(description="Meta in which matches happened, e.g. OP06")
                official: bool = Field(default=False, description="Whether the match is originated from an official tournament")
                is_reverse: bool = Field(description="Whether its the reverse match", primary_key=True)
                source: DataSource | str = Field(description="Origin of the match. In case of an unofficial match it can be the session id.")
                tournament_id: str | None = Field(None, description="Unique id of single tournament")
                tournament_round: int | None = Field(None, description="Round during which the match happened.")
                tournament_phase: int | None = Field(None, description="Phase during which the match happened.")
                tournament_table: int | None = Field(None, description="Table number of the match (for all phase types except live brackets).")
                player_id: str | None = Field(None, description="Username/ID used to uniquely identify the player. Does not change between tournaments.")
                opponent_player_id: str | None = Field(None, description="Username/ID used to uniquely identify the opponent. Does not change between tournaments.")
                match_timestamp: datetime = Field(description="Approximate timestamp when the match happened")
                create_timestamp: datetime = Field(default_factory=datetime.now, description="Creation timestamp when the insert in BQ happened")
        """

        class MatchPairingResult(BaseModel):
            id: str
            result: MatchResult
            player_id: str
            opponent_player_id: str
            is_reverse: bool
            match_timestamp: datetime

        for pairing in json_res:
            id = uuid4().hex
            winner = pairing["winner"]
            # Assumes 30 minutes for each match
            match_timestamp = response.meta["date"] + timedelta(minutes=30*pairing["round"])
            # list of 2 matches (one match + one reverse match)
            match_results: list[MatchPairingResult] = []
            if str(winner) in ["0", "-1"]:
                match_results.append(MatchPairingResult(id=id, result=MatchResult.DRAW, player_id=pairing["player1"],
                                                        opponent_player_id=pairing["player2"], is_reverse=False, match_timestamp=match_timestamp))
                match_results.append(MatchPairingResult(id=id, result=MatchResult.DRAW, player_id=pairing["player2"],
                                                        opponent_player_id=pairing["player1"], is_reverse=True, match_timestamp=match_timestamp))
            else:
                player_id = pairing["winner"]
                opponent_player_id = pairing["player1"] if player_id != pairing["player1"] else pairing["player2"]
                match_results.append(MatchPairingResult(id=id, result=MatchResult.WIN, player_id=player_id,
                                                        opponent_player_id=opponent_player_id, is_reverse=False, match_timestamp=match_timestamp))
                match_results.append(MatchPairingResult(id=id, result=MatchResult.LOSE, player_id=opponent_player_id,
                                                        opponent_player_id=player_id, is_reverse=True, match_timestamp=match_timestamp))
            assert len(match_results) == 2

            for match_result in match_results:
                match = Match(
                    leader_id=response.meta["player_id2leader_id"][match_result.player_id],
                    opponent_id=response.meta["player_id2leader_id"][match_result.opponent_player_id],
                    meta_format=response.meta["meta_format"],
                    tournament_id=response.meta["id"],
                    source=DataSource.LIMITLESS,
                    official=response.meta["official"],
                    **{**match_result, **pairing}
                )
                yield match