import logging
from datetime import datetime, timedelta
from uuid import uuid4

import scrapy
import json

from google.cloud import bigquery
from pydantic import BaseModel, ValidationError

from op_tcg.backend.crawling.items import TournamentItem
from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.models.cards import Card, CardPrice
from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.decklists import Decklist
from op_tcg.backend.models.input import MetaFormat, meta_format2release_datetime, MetaFormatRegion
from op_tcg.backend.models.tournaments import Tournament, TournamentStanding
from op_tcg.backend.models.matches import Match, MatchResult
from op_tcg.backend.utils.database import create_decklist_id


class LimitlessTournamentSpider(scrapy.Spider):
    name = "limitless_tournaments"

    meta_formats: list[MetaFormat]
    api_token: str
    num_tournament_limit: int

    def get_already_crawled_tournament_ids(self) -> dict[str, bool]:
        """returns tournaments already crawled and if they had decklists available back than"""
        tournament_id2decklists: dict[str, bool] = {}
        for tournament_id in self.bq_client.query(
                f"SELECT id, decklists FROM `{self.tournament_table.full_table_id.replace(':', '.')}`").result():
            tournament_id2decklists[tournament_id["id"]] = tournament_id["decklists"]
        return tournament_id2decklists

    def get_already_crawled_card_ids(self) -> list[str]:
        """returns card ids already crawled"""
        card_ids: list[str] = []
        for card_row in self.bq_client.query(
                f"SELECT id FROM `{self.card_table.full_table_id.replace(':', '.')}`").result():
            card_ids.append(card_row["id"])
        return card_ids


    def get_bq_decklist_ids(self) -> list[str]:
        """Returns list of decklist ids stored in bq"""
        decklist_ids: list[str] = []
        for card_row in self.bq_client.query(
                f"SELECT id FROM `{self.decklist_table.full_table_id.replace(':', '.')}`").result():
            decklist_ids.append(dict(card_row)["id"])
        return decklist_ids

    def start_requests(self):
        self.bq_client = bigquery.Client(location="europe-west3")
        self.match_table = get_or_create_table(Match, client=self.bq_client)
        self.tournament_table = get_or_create_table(Tournament, client=self.bq_client)
        self.tournament_standing_table = get_or_create_table(TournamentStanding, client=self.bq_client)
        self.decklist_table = get_or_create_table(Decklist, client=self.bq_client)
        self.card_table = get_or_create_table(Card, client=self.bq_client)
        self.card_price_table = get_or_create_table(CardPrice, client=self.bq_client)
        self.known_tournament_id2contains_decklists = self.get_already_crawled_tournament_ids()
        self.already_crawled_card_ids = self.get_already_crawled_card_ids()
        self.decklist_ids_crawled = self.get_bq_decklist_ids()


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
        # public tournaments are considers as official
        official = json_res["isPublic"]
        proceed_crawling = True
        if tournament_id in self.known_tournament_id2contains_decklists:
            # decklist is now available, but not yet in db
            if json_res["decklists"]:
                proceed_crawling = True
            else:
                proceed_crawling = False
                print(
                    f"Ignore tournament with id {tournament_id} as its already known and contains no new decklist information")

        if proceed_crawling:
            url = f"https://play.limitlesstcg.com/api/tournaments/{tournament_id}/standings?key={self.api_token}"
            yield scrapy.Request(url=url, callback=self.parse_tournament_standings,
                                 meta={"official": official, **json_res})

    def get_meta_format(self, all_decklists: list[dict[str, int]], tournament_date: datetime) -> MetaFormat | str:
        decklist_meta_formats: list[str] = [card_id.split("-")[0] for decklist in all_decklists for card_id in
                                            decklist.keys() if card_id[:2] == "OP"]
        if decklist_meta_formats:
            latest_meta_format = sorted(decklist_meta_formats, reverse=True)[0]
            return MetaFormat(latest_meta_format) if latest_meta_format in MetaFormat.to_list(only_after_release=False) else latest_meta_format
        for meta_format in sorted(MetaFormat.to_list(), reverse=True):
            if tournament_date > meta_format2release_datetime(meta_format):
                return meta_format
        raise ValueError("tournament could not be matched to meta_format")

    def parse_tournament_standings(self, response):
        json_res: list[dict[str, str]] = json.loads(response.body)
        player_id2leader_id: dict[str, str] = {}
        all_decklists: list[dict[str, int]] = []
        tournament_standings: list[TournamentStanding] = []
        bq_decklists: list[Decklist] = []
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
                decklist_id = create_decklist_id(decklist)
                bq_decklists.append(Decklist(
                    id=decklist_id,
                    leader_id=leader_id,
                    decklist=decklist
                ))
            try:
                tournament_standings.append(TournamentStanding(tournament_id=response.meta["id"], leader_id=leader_id,
                                                               decklist=decklist, decklist_id=decklist_id,
                                                               **{k: v for k, v in standing.items() if
                                                                  k not in ["decklist"]}))
            except ValidationError as e:
                print(e)
            player_id2leader_id[standing["player"]] = leader_id

        meta_format: MetaFormat | str = self.get_meta_format(all_decklists,
                                                       tournament_date=datetime.strptime(response.meta["date"],
                                                                                         "%Y-%m-%dT%H:%M:%S.%fZ"))
        url = f"https://play.limitlesstcg.com/api/tournaments/{response.meta['id']}/pairings?key={self.api_token}"
        # only add matches, if all players have a leader information
        if not any(leader_id == None for leader_id in player_id2leader_id.values()):
            yield scrapy.Request(url=url, callback=self.parse_tournament_pairings,
                                 meta={"player_id2leader_id": player_id2leader_id,
                                       "bq_decklists": bq_decklists,
                                       "meta_format": meta_format,
                                       "tournament_standings": tournament_standings, **response.meta})
        else:
            tournament = Tournament(source=DataSource.LIMITLESS,
                                    meta_format=meta_format,
                                    meta_format_region=MetaFormatRegion.WEST, **response.meta)
            yield self.get_tournamend_item(tournament=tournament, tournament_standings=tournament_standings, decklists=bq_decklists)

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
                                meta_format_region=MetaFormatRegion.WEST,
                                **response.meta)
        yield self.get_tournamend_item(tournament=tournament,
                                       tournament_standings=response.meta["tournament_standings"],
                                       decklists=response.meta["bq_decklists"],
                                       matches=matches)

    def get_tournamend_item(self, tournament: Tournament, tournament_standings: list[TournamentStanding],
                            matches: list[Match] = None, decklists: list[Decklist] = None) -> TournamentItem:
        matches = matches if matches is not None else []  # if no matches exist returns an empy list
        return TournamentItem(tournament=tournament, tournament_standings=tournament_standings, matches=matches, decklists=decklists)

    def closed(self, reason):
        logging.info(f"Finished spider")
