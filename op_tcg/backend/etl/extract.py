import json
import os
from pathlib import Path

from op_tcg.backend.models.input import AllMetaLeaderMatches, LimitlessLeaderMetaMatches


def read_json_files(data_dir: str) -> AllMetaLeaderMatches:
    documents = []
    for filename in os.listdir(data_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(data_dir, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
                doc = LimitlessLeaderMetaMatches(**data)
                documents.append(doc)
    return AllMetaLeaderMatches(documents=documents)


def get_leader_ids(data_dir: Path) -> list[str]:
    """Returns list of leader ids e.g. OP01-001 for crawling the limitless site"""
    leaders = []
    matches = read_json_files(data_dir)
    for leader_matches in matches:
        leaders_in_matches = [l.leader_id for l in leader_matches.matches]
        leaders.extend(leaders_in_matches)
    leaders = list(set(leaders))
    return leaders