import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from op_tcg.backend.models.input import AllLeaderMetaDocs, LimitlessLeaderMetaDoc, MetaFormat
from op_tcg.backend.models.leader import OPTcgLanguage, Leader, OPTcgColor, OPTcgAttribute


def read_json_files(data_dir: str | Path) -> AllLeaderMetaDocs:
    documents = []
    for filename in os.listdir(data_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(data_dir, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
                doc = LimitlessLeaderMetaDoc(**data)
                documents.append(doc)
    return AllLeaderMetaDocs(documents=documents)


def get_leader_ids(data_dir: Path) -> list[str]:
    """Returns list of leader ids e.g. OP01-001 for crawling the limitless site"""
    leader_ids = []
    matches = read_json_files(data_dir)
    for leader_matches in matches.documents:
        leaders_in_matches = [l.leader_id for l in leader_matches.matches]
        leader_ids.extend(leaders_in_matches)
    leader_ids = list(set(leader_ids))
    return leader_ids


def limitless2bq_leader(leader_id, language: OPTcgLanguage = OPTcgLanguage.EN) -> Leader:
    limitless_url = f"https://onepiece.limitlesstcg.com/cards/{language}/{leader_id}?v=0"
    response = requests.get(limitless_url)
    response.raise_for_status()
    html_str = response.text
    soup = BeautifulSoup(html_str)

    # extract text data
    leader_name = soup.find('span', {'class': 'card-text-name'}).text
    colors = soup.find('p', {'class': 'card-text-type'}).find("span", {'data-tooltip': 'Color'}).text.strip().split("/")
    leader_colors = [OPTcgColor(c) for c in colors]
    leader_life = int(re.search(r'(\d+)(?=\s*Life)', soup.find('p', {'class': 'card-text-type'}).text).group(0))
    leader_power = int(re.search(r'(\d+)(?=\s*Power)', soup.find('p', {'class': 'card-text-section'}).text).group(0))
    attributes = soup.findAll('p', {'class': 'card-text-section'})[0].find("span", {'data-tooltip': 'Attribute'}).text.strip().split("/")
    leader_attributes = [OPTcgAttribute(a) for a in attributes]
    leader_ability = soup.findAll('div', {'class': 'card-text-section'})[1].text.strip()
    leader_fractions = soup.findAll('div', {'class': 'card-text-section'})[2].text.strip().split("/")

    # image data
    # TODO: Find good source for avatar icon
    leader_avatar_url = f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{leader_id.split('-')[0]}/{leader_id}_{language.upper()}.webp"
    leader_image_url = leader_avatar_url
    leader_aa_image_url = f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{leader_id.split('-')[0]}/{leader_id}_p1_{language.upper()}.webp"

    try:
        release_meta = MetaFormat(leader_id.split("-")[0])
    except ValueError:
        # Some release_meta can not be extracted from id directly e.g. from preconstructed decks
        release_meta = None

    return Leader(
        id=leader_id,
        name=leader_name,
        life=leader_life,
        power=leader_power,
        release_meta=release_meta,
        avatar_icon_url=leader_avatar_url,
        image_url=leader_image_url,
        image_aa_url=leader_aa_image_url,
        colors=leader_colors,
        attributes=leader_attributes,
        ability=leader_ability,
        fractions=leader_fractions,
        language=language
    )
