import op_tcg
import json
from pathlib import Path
from op_tcg.crawling.matches.matches.items import LimitlessLeaderMetaMatches

class MatchesPipeline:
    def process_item(self, item: LimitlessLeaderMetaMatches, spider):
        target_dir = Path(op_tcg.__file__).parent.parent / "data" / "limitless"
        target_dir.mkdir(exist_ok=True, parents=True)
        with open(target_dir / f"{item.leader_id}_{item.meta_format}.json", "w") as fp:
            json.dump(item.model_dump(), fp)
        return item
