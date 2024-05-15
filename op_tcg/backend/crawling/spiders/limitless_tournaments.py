import scrapy
import requests
import json
from pathlib import Path
from bs4 import BeautifulSoup

from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.input import LimitlessMatch, LimitlessLeaderMetaDoc, MetaFormat
from op_tcg.backend.etl.extract import read_json_files
from op_tcg.backend.models.tournaments import Tournament


class LimitlessTournamentSpider(scrapy.Spider):
    name = "limitless_tournaments"

    meta_formats: list[MetaFormat]
    api_token: str


    def meta_format2limitless_formats(self, meta_format: MetaFormat) -> list[str]:
        limitless_games = requests.get(f"https://play.limitlesstcg.com/api/games?key={self.api_token}")
        optcg_formats: dict[str, str] = [limitless_game for limitless_game in limitless_games if "OPTCG" == limitless_game["id"]][0]["formats"]
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
            url = f"https://play.limitlesstcg.com/api/tournaments/{tournament['id']}/details?key={self.api_token}"
            yield scrapy.Request(url=url, callback=self.parse_tournament, meta={"meta_format": meta_format, **tournament})
            url = f"https://play.limitlesstcg.com/api/tournaments/{tournament['id']}/standings?key={self.api_token}"
            yield scrapy.Request(url=url, callback=self.parse_tournament_standings, meta={**tournament})
            url = f"https://play.limitlesstcg.com/api/tournaments/{tournament['id']}/pairings?key={self.api_token}"
            yield scrapy.Request(url=url, callback=self.parse_tournament_pairings, meta={**tournament})

    def parse_tournament(self, response):
        json_res: dict[str, str] = json.loads(response.body)
        tournament = Tournament(official=True, source=DataSource.LIMITLESS, **json_res)
        yield tournament

    def parse_tournament_standings(self, response):
        json_res: dict[str, str] = json.loads(response.body)
        # TODO

    def parse_tournament_pairings(self, response):
        json_res: dict[str, str] = json.loads(response.body)
        # TODO
