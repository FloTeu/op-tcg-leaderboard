import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from op_tcg.backend.models.input import AllLeaderMetaDocs, LimitlessLeaderMetaDoc, MetaFormat
from op_tcg.backend.models.leader import Leader
from op_tcg.backend.models.cards import OPTcgColor, OPTcgAttribute, OPTcgLanguage, OPTcgTournamentStatus, \
    OPTcgCardCatagory, BaseCard, Card


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


def limitless_soup2base_card(card_id: str, language: OPTcgLanguage, soup: BeautifulSoup) -> BaseCard:
    # extract text data
    card_name = soup.find('span', {'class': 'card-text-name'}).text
    card_category = OPTcgCardCatagory(
        soup.find('p', {'class': 'card-text-type'}).find("span", {'data-tooltip': 'Category'}).text.strip())
    colors = soup.find('p', {'class': 'card-text-type'}).find("span", {'data-tooltip': 'Color'}).text.strip().split("/")
    parsed_colors = [OPTcgColor(c) for c in colors]
    ability = soup.findAll('div', {'class': 'card-text-section'})[1].text.strip()
    fractions = soup.findAll('div', {'class': 'card-text-section'})[2].text.strip().split("/")
    tournament_status = OPTcgTournamentStatus(
        soup.find("div", {'class': 'card-legality-badge'}).findAll("div")[1].text.strip())

    # create image urls
    image_url = f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{card_id.split('-')[0]}/{card_id}_{language.upper()}.webp"
    # Note: -2 to remove standard design and header row
    num_aa_designs = len(soup.find("table", {'class': 'card-prints-versions'}).findAll("tr")) - 2
    aa_image_urls = []
    for i in range(num_aa_designs):
        aa_image_urls.append(
            f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{card_id.split('-')[0]}/{card_id}_p{i + 1}_{language.upper()}.webp")

    try:
        release_meta = MetaFormat(card_id.split("-")[0])
    except ValueError:
        # Some release_meta can not be extracted from id directly e.g. from preconstructed decks
        release_meta = None

    return BaseCard(
        id=card_id,
        name=card_name,
        release_meta=release_meta,
        image_url=image_url,
        image_aa_urls=aa_image_urls,
        colors=parsed_colors,
        ability=ability,
        tournament_status=tournament_status,
        fractions=fractions,
        language=language,
        card_category=card_category,
    )


def limitless2bq_card(card_id, language: OPTcgLanguage = OPTcgLanguage.EN) -> Card:
    limitless_url = f"https://onepiece.limitlesstcg.com/cards/{language}/{card_id}?v=0"
    response = requests.get(limitless_url)
    response.raise_for_status()
    html_str = response.text
    soup = BeautifulSoup(html_str)

    # extract text data
    base_card: BaseCard = limitless_soup2base_card(card_id, language, soup)
    life = None
    cost = None
    power = None
    counter = None
    attributes = []
    if base_card.card_category in [OPTcgCardCatagory.CHARACTER, OPTcgCardCatagory.EVENT, OPTcgCardCatagory.STAGE]:
        cost = int(
            re.search(r'(\d+)(?=\s*Cost)', soup.find('p', {'class': 'card-text-type'}).text).group(0))
    if base_card.card_category in [OPTcgCardCatagory.LEADER, OPTcgCardCatagory.CHARACTER]:
        power = int(
            re.search(r'(\d+)(?=\s*Power)', soup.find('p', {'class': 'card-text-section'}).text).group(0))
        attributes = soup.findAll('p', {'class': 'card-text-section'})[0].find("span", {
            'data-tooltip': 'Attribute'}).text.strip().split("/")
        attributes = [OPTcgAttribute(a) for a in attributes]
    if base_card.card_category == OPTcgCardCatagory.LEADER:
        life = int(re.search(r'(\d+)(?=\s*Life)', soup.find('p', {'class': 'card-text-type'}).text).group(0))
    if base_card.card_category == OPTcgCardCatagory.CHARACTER:
        # regex which extracts integers with 4 digits and + or minus prefix
        pattern = r"[+-]\d{4}"
        matches = re.search(pattern, soup.findAll('p', {'class': 'card-text-section'})[0].text)
        if matches:
            counter = int(matches.group(0))

    return Card(
        attributes=attributes,
        power=power,
        cost=cost,
        counter=counter,
        life=life,
        **base_card.model_dump(),
    )


def limitless2bq_leader(card_id, language: OPTcgLanguage = OPTcgLanguage.EN) -> Leader:
    limitless_url = f"https://onepiece.limitlesstcg.com/cards/{language}/{card_id}?v=0"
    response = requests.get(limitless_url)
    response.raise_for_status()
    html_str = response.text
    soup = BeautifulSoup(html_str)

    # extract text data
    base_card: BaseCard = limitless_soup2base_card(card_id, language, soup)
    leader_life = int(re.search(r'(\d+)(?=\s*Life)', soup.find('p', {'class': 'card-text-type'}).text).group(0))
    leader_power = int(re.search(r'(\d+)(?=\s*Power)', soup.find('p', {'class': 'card-text-section'}).text).group(0))
    attributes = soup.findAll('p', {'class': 'card-text-section'})[0].find("span", {
        'data-tooltip': 'Attribute'}).text.strip().split("/")
    leader_attributes = [OPTcgAttribute(a) for a in attributes]

    # TODO: Find good source for avatar icon

    return Leader(
        id=base_card.id,
        name=base_card.name,
        life=leader_life,
        power=leader_power,
        release_meta=base_card.release_meta,
        avatar_icon_url=base_card.image_url,
        image_url=base_card.image_url,
        image_aa_url=base_card.image_aa_urls[0],
        colors=base_card.colors,
        attributes=leader_attributes,
        ability=base_card.ability,
        fractions=base_card.fractions,
        language=base_card.language
    )
