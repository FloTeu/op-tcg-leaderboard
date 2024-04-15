import scrapy
import op_tcg
from pathlib import Path
from bs4 import BeautifulSoup
from op_tcg.backend.models.input import LimitlessMatch, LimitlessLeaderMetaMatches, MetaFormat
from op_tcg.backend.etl.extract import read_json_files


class LimitlessSpider(scrapy.Spider):
    name = "limitless"

    meta_formats: list[MetaFormat]
    leader_ids: list[str]

    @staticmethod
    def get_leaders(data_dir: Path | None = None) -> list[str]:
        """Returns list of leader ids e.g. OP01-001 for crawling the limitless site"""
        #TODO: Read from dynamically updated source e.g. big query
        leaders = ["OP01-001"]
        #leaders = ['ST02-001', 'OP03-040', 'OP04-019', 'OP04-040', 'ST03-001', 'OP03-022', 'P-047', 'OP06-001', 'ST05-001', 'ST09-001', 'ST01-001', 'OP05-098', 'ST08-001', 'OP02-072', 'OP02-093', 'OP03-077', 'OP04-039', 'OP03-001', 'OP03-076', 'ST13-003', 'OP03-021', 'OP01-091', 'OP02-071', 'OP06-042', 'ST10-001', 'OP02-001', 'OP05-041', 'ST10-003', 'OP04-058', 'OP01-001', 'OP01-060', 'OP02-049', 'ST13-002', 'OP01-003', 'OP06-080', 'OP01-002', 'OP01-061', 'OP06-022', 'OP01-062', 'OP05-002', 'ST13-001', 'OP06-021', 'OP01-031', 'ST11-001', 'OP02-026', 'ST12-001', 'OP03-099', 'OP03-058', 'ST10-002', 'OP05-001', 'OP05-060', 'ST07-001', 'OP04-020', 'OP04-001', 'OP06-020', 'OP05-022', 'ST04-001', 'OP02-025', 'OP02-002']
        if data_dir:
            leaders = []
            matches = read_json_files(data_dir)
            for leaader_matches in matches:
                leaders_in_matches = [l.leader_id for l in leaader_matches.matches]
                leaders.extend(leaders_in_matches)
            leaders = list(set(leaders))
        return leaders


    def start_requests(self):
        data_dir = Path(op_tcg.__file__).parent.parent / "data" / "limitless"
        leader_ids = self.leader_ids if self.leader_ids else ["OP01-001"]
        meta_formats = self.meta_formats if self.meta_formats else [MetaFormat.OP01]
        urls = []
        for leader in leader_ids:
            for meta_format in meta_formats:
                urls.append(f"https://play.limitlesstcg.com/decks/{leader}/matchups?game=OP&set={meta_format.value}")

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    @staticmethod
    def extract_leader_id(url):
        return url.split('/')[2]

    @staticmethod
    def parse_score(score_str):
        return [int(x) for x in score_str.split(' - ')]

    def parse_to_pydantic(self, row) -> LimitlessMatch:
        leader_name = row['data-name']
        leader_id = self.extract_leader_id(row.select_one('td a')['href'])
        num_matches = int(row['data-matches'])
        win_rate = float(row['data-winrate'])
        score_str = row.select_one('td.nowrap').text
        score_win, score_lose, score_draw = self.parse_score(score_str)

        return LimitlessMatch(
            leader_name=leader_name,
            leader_id=leader_id,
            num_matches=num_matches,
            score_win=score_win,
            score_lose=score_lose,
            score_draw=score_draw,
            win_rate=win_rate
        )

    def parse(self, response):
        leader = response.url.split("/")[-2]
        meta_format = MetaFormat(response.css('.format::text').get().split(" ")[0])
        filename = f"limitless_{leader}_{meta_format}.html"
        data_dir = Path(op_tcg.__file__).parent.parent / "data" / "html"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / filename).write_bytes(response.body)

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('table.striped tr')[1:]  # Skip the header row

        # List to hold the Pydantic objects
        matches = []

        # Iterate over the rows and create Pydantic objects
        for row in rows:
            try:
                matches.append(self.parse_to_pydantic(row))
            except Exception as e:
                print(f"Error with row {row} {e}")


        leader_matches = LimitlessLeaderMetaMatches(
            leader_id=leader,
            meta_format=meta_format,
            matches=matches
        )
        yield leader_matches