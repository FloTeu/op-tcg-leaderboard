import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from op_tcg.backend.models.input import AllLeaderMetaDocs, LimitlessLeaderMetaDoc, MetaFormat
from op_tcg.backend.models.leader import Leader
from op_tcg.backend.models.cards import OPTcgColor, OPTcgAttribute, OPTcgLanguage, OPTcgTournamentStatus, \
    OPTcgCardCatagory, BaseCard, Card, OPTcgCardRarity, LimitlessCardData, CardPrice, CardCurrency

def replace_linebreak_whitespace(text: str) -> str:
    """
    Example:
        Input: "\n                    [Main] Draw 2 cards.\n        \n                    \n            [Trigger] Activate this card's [Main] effect.\n        \n"
        Output: "\n[Main] Draw 2 cards.\n[Trigger] Activate this card's [Main] effect.\n        \n    "
    """
    # This regex matches a linebreak (\n) followed by at least two whitespace characters
    pattern = r'(\n\s{2,})(?=\[)'
    # Replace the matched pattern with a linebreak followed by zero whitespace
    replaced_text = re.sub(pattern, '\n', text)
    return replaced_text

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

def get_card_image_url(card_id: str, language: OPTcgLanguage, aa_version: int=0):
    if aa_version == 0:
        return f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{card_id.split('-')[0]}/{card_id}_{language.upper()}.webp"
    else:
        return f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{card_id.split('-')[0]}/{card_id}_p{aa_version}_{language.upper()}.webp"

def limitless_soup2base_card(card_id: str, language: OPTcgLanguage, soup: BeautifulSoup, aa_version: int=0) -> BaseCard:
    # extract text data
    card_name = soup.find('span', {'class': 'card-text-name'}).text
    card_category = OPTcgCardCatagory(
        soup.find('p', {'class': 'card-text-type'}).find("span", {'data-tooltip': 'Category'}).text.strip())
    colors = soup.find('p', {'class': 'card-text-type'}).find("span", {'data-tooltip': 'Color'}).text.strip().split("/")
    parsed_colors = [OPTcgColor(c) for c in colors]

    # Extract text and replace <br/> tags with newlines
    text_section = soup.findAll('div', {'class': 'card-text-section'})[1]
    for br in text_section.find_all('br'):
        br.replace_with('')
    ability = replace_linebreak_whitespace(text_section.text).strip()
    fractions = soup.findAll('div', {'class': 'card-text-section'})[2].text.strip().split("/")
    tournament_status = OPTcgTournamentStatus(
        soup.find("div", {'class': 'card-legality-badge'}).findAll("div")[1].text.strip())
    release_set_details = soup.find("div", {'class': 'card-prints-current'})
    if card_id[0] == "P":
        rarity = OPTcgCardRarity.PROMO
    else:
        rarity = OPTcgCardRarity(release_set_details.findAll("span")[1].text.strip())

    # create image urls
    image_url = get_card_image_url(card_id, language, aa_version=aa_version)

    return BaseCard(
        id=card_id,
        name=card_name,
        image_url=image_url,
        aa_version=aa_version,
        colors=parsed_colors,
        ability=ability,
        tournament_status=tournament_status,
        types=fractions,
        rarity=rarity,
        language=language,
        card_category=card_category,
        release_set_id=""
    )



def limitless_soup2base_cards(card_id: str, language: OPTcgLanguage, soup: BeautifulSoup, num_aa_designs: int=0) -> list[BaseCard]:
    base_cards: list[BaseCard] = []
    for i in range(num_aa_designs + 1):
        base_cards.append(limitless_soup2base_card(card_id, language, soup, aa_version=i))
    return base_cards


def parse_price(column: str, table_cell: Tag) -> tuple[CardCurrency, float] | tuple[str, str]:
    try:
        currency = CardCurrency(column.lower())
        if currency == CardCurrency.EURO:
            # assumes format: '12.52€'
            return currency, float(table_cell.text.strip()[:-1])
        elif currency == CardCurrency.US_DOLLAR:
            # assumes format: '$14.40'
            return currency, float(table_cell.text.strip()[1:])
        else:
            raise NotImplementedError
    except ValueError:
        # if column is not a valid currency, we return the table cell as string
        return column, table_cell.text.strip()

def extract_card_prices(card_id: str, language: OPTcgLanguage, soup: BeautifulSoup) -> list[CardPrice]:
    card_prices: list[CardPrice] = []
    columns = [col.text for col in soup.find("table", {'class': 'card-prints-versions'}).find("tr").findAll("th")]
    # Note: skip header row
    for aa_version, price_row in enumerate(soup.find("table", {'class': 'card-prints-versions'}).findAll("tr")[1:]):
        col2value = {
            parse_price(columns[i], cell)[0]: parse_price(columns[i], cell)[1] for i, cell in enumerate(price_row.findAll("td"))
        }
        for col, value in col2value.items():
            if col in CardCurrency.to_list():
                card_prices.append(
                    CardPrice(
                        card_id=card_id,
                        language=language,
                        aa_version=aa_version,
                        price=value,
                        currency=CardCurrency(col)
                    )
                )
    return card_prices


def base_card2bq_card(base_card: BaseCard, soup: BeautifulSoup) -> Card:
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
            'data-tooltip': 'Attribute'}).text.strip().removeprefix("card.attribute.").split("/")
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

def crawl_limitless_card(card_id, language: OPTcgLanguage = OPTcgLanguage.EN) -> LimitlessCardData:
    base_url = "https://onepiece.limitlesstcg.com"
    limitless_url = f"{base_url}/cards/{language}/{card_id}?v=0"
    response = requests.get(limitless_url)
    response.raise_for_status()
    html_str = response.text
    soup = BeautifulSoup(html_str)

    # extract text data
    card_prices = extract_card_prices(card_id, language, soup)
    num_aa_designs=len(set([card_price.aa_version for card_price in card_prices if card_price.aa_version != 0]))
    base_cards: list[BaseCard] = limitless_soup2base_cards(card_id, language, soup, num_aa_designs=num_aa_designs)
    return LimitlessCardData(
        cards=[base_card2bq_card(base_card, soup) for base_card in base_cards],
        card_prices=card_prices
    )

def limitless2bq_leader(card_id, language: OPTcgLanguage = OPTcgLanguage.EN) -> Leader:
    limitless_url = f"https://onepiece.limitlesstcg.com/cards/{language}/{card_id}?v=0"
    response = requests.get(limitless_url)
    response.raise_for_status()
    html_str = response.text
    soup = BeautifulSoup(html_str)

    # extract text data
    base_card: BaseCard = limitless_soup2base_cards(card_id, language, soup)
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
        fractions=base_card.types,
        language=base_card.language
    )
