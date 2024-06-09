from datetime import datetime, timedelta
from uuid import uuid4

import scrapy
import json

from google.cloud import bigquery
from pydantic import BaseModel

from op_tcg.backend.crawling.items import TournamentItem
from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.etl.transform import meta_format2release_datetime
from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.tournaments import Tournament, TournamentStanding
from op_tcg.backend.models.matches import Match, MatchResult


class LimitlessTournamentSpider(scrapy.Spider):
    name = "limitless_tournaments"

    meta_formats: list[MetaFormat]
    api_token: str
    num_tournament_limit: int

    def get_already_crawled_tournament_ids(self) -> dict[str, bool]:
        """returns tournaments already crawled and if they had decklists available back than"""
        tournament_id2decklists: dict[str, bool] = {}
        for tournament_id in self.bq_client.query(f"SELECT id, decklists FROM `{self.tournament_table.full_table_id.replace(':','.')}`").result():
            tournament_id2decklists[tournament_id["id"]] = tournament_id["decklists"]
        return tournament_id2decklists

    def start_requests(self):
        self.bq_client = bigquery.Client(location="europe-west3")
        self.match_table = get_or_create_table(Match, client=self.bq_client)
        self.tournament_table = get_or_create_table(Tournament, client=self.bq_client)
        self.tournament_standing_table = get_or_create_table(TournamentStanding, client=self.bq_client)
        self.known_tournament_id2contains_decklists = self.get_already_crawled_tournament_ids()

        url = f"https://play.limitlesstcg.com/api/tournaments?game=OP&limit={self.num_tournament_limit}&key={self.api_token}"
        yield scrapy.Request(url=url, callback=self.parse_tournaments)

    def parse_tournaments(self, response):
        json_res: list[dict[str, str]] = json.loads(response.body)
        for tournament in json_res:
            id = tournament["id"]
            # ignore tournaments which already exist in db and where decklist is known
            if id in self.known_tournament_id2contains_decklists and self.known_tournament_id2contains_decklists[id]:
                print(f"Ignore tournament with id {id} as its already known")
                continue

            url = f"https://play.limitlesstcg.com/api/tournaments/{id}/details?key={self.api_token}"
            yield scrapy.Request(url=url, callback=self.parse_tournament)

    def parse_tournament(self, response):
        json_res: dict[str, str] = json.loads(response.body)
        tournament_id = json_res['id']
        # online offline and public tournaments are considers as official
        official = not json_res["isOnline"] and json_res["isPublic"]
        proceed_crawling = True
        if tournament_id in self.known_tournament_id2contains_decklists:
            # decklist is now available, but not yet in db
            if json_res["decklists"]:
                proceed_crawling = True
            else:
                proceed_crawling = False
                print(f"Ignore tournament with id {tournament_id} as its already known and contains no new decklist information")


        if proceed_crawling:
            url = f"https://play.limitlesstcg.com/api/tournaments/{tournament_id}/standings?key={self.api_token}"
            yield scrapy.Request(url=url, callback=self.parse_tournament_standings,
                                 meta={"official": official, **json_res})


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
        tournament_standings: list[TournamentStanding] = []
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

            tournament_standings.append(TournamentStanding(tournament_id=response.meta["id"], leader_id=leader_id,
                                                     decklist=decklist,
                                                     **{k: v for k, v in standing.items() if k not in ["decklist"]}))
            player_id2leader_id[standing["player"]] = leader_id


        meta_format = self.get_meta_format(all_decklists,
            tournament_date = datetime.strptime(response.meta["date"], "%Y-%m-%dT%H:%M:%S.%fZ"))
        url = f"https://play.limitlesstcg.com/api/tournaments/{response.meta['id']}/pairings?key={self.api_token}"
        # only add matches, if all players have a leader information
        if not any(leader_id == None for leader_id in player_id2leader_id.values()):
            yield scrapy.Request(url=url, callback=self.parse_tournament_pairings,
                                 meta={"player_id2leader_id": player_id2leader_id, "meta_format": meta_format,
                                       "tournament_standings": tournament_standings, **response.meta})
        else:
            tournament = Tournament(source=DataSource.LIMITLESS,
                                    meta_format=meta_format, **response.meta)
            yield self.get_tournamend_item(tournament=tournament, tournament_standings=tournament_standings)



    def parse_tournament_pairings(self, response):
        json_res: list[dict[str, str]] = json.loads(response.body)
        matches: list[Match] = []

        class MatchPairingResult(BaseModel):
            id: str
            result: MatchResult
            player_id: str
            opponent_player_id: str
            is_reverse: bool
            match_timestamp: datetime

        for pairing in json_res:
            if "player2" not in pairing:
                # case player 2 dropped or did not exist
                # ignore this match as we dont have a opponent leader card for a valid match
                continue
            id = uuid4().hex  # define new unique match id
            winner = pairing["winner"]
            if "table" in pairing:
                pairing["table"] = str(pairing["table"])
            if "match" in pairing:
                pairing["match"] = str(pairing["match"])
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
                matches.append(Match(
                    leader_id=response.meta["player_id2leader_id"][match_result.player_id],
                    opponent_id=response.meta["player_id2leader_id"][match_result.opponent_player_id],
                    meta_format=response.meta["meta_format"],
                    tournament_id=response.meta["id"],
                    source=DataSource.LIMITLESS,
                    official=response.meta["official"],
                    **{**match_result.model_dump(), **pairing}
                ))

        tournament = Tournament(source=DataSource.LIMITLESS,
                                **response.meta)
        yield self.get_tournamend_item(tournament=tournament, tournament_standings=response.meta["tournament_standings"], matches=matches)


    def get_tournamend_item(self, tournament: Tournament, tournament_standings: list[TournamentStanding], matches: list[Match] = None) -> TournamentItem:
        matches = matches if matches is not None else []  # if no matches exist returns an empy list
        return TournamentItem(tournament=tournament, tournament_standings=tournament_standings, matches=matches)