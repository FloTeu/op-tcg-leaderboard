from urllib.parse import quote_plus
from op_tcg.backend.models.cards import LatestCardPrice, CardCurrency, ExtendedCardData


def get_marketplace_link(card_id: str, card_name: str, release_set_name: str | None, currency: CardCurrency) -> tuple[str, str]:
    """
    Generate the marketplace URL and display text for a card based on currency.

    Args:
        card_id: The card ID (e.g. OP01-001)
        card_name: The card name
        release_set_name: The release set name (optional, used for TCGplayer)
        currency: The currency (EURO for Cardmarket, US_DOLLAR for TCGplayer)

    Returns:
        A tuple containing (url, display_text)
    """
    if currency == CardCurrency.EURO:
        query = quote_plus(card_id)
        url = f"https://www.cardmarket.com/en/OnePiece/Products/Search?searchString={query}&category=-1&mode=gallery"
        text = "View on Cardmarket"
    else:
        # For TCGplayer use name + set name if available
        q_str = f"{card_name} {release_set_name}".strip() if release_set_name else card_name
        query = quote_plus(q_str)
        url = f"https://www.tcgplayer.com/search/one-piece-card-game/product?q={query}&productLineName=one-piece-card-game"
        text = "View on TCGplayer"

    return url, text


def get_decklist_price(decklist: dict[str, int], card_id2card_data: dict[str, LatestCardPrice],
                       currency: CardCurrency = CardCurrency.EURO) -> float:
    """Calculated the euro or us dollar price for a given decklist

    Note: This function is not placed in decklist.py to prevent a circular import error
    """
    deck_price = 0.0
    for card_id, count in decklist.items():
        card_data = card_id2card_data.get(card_id, None)
        if currency == CardCurrency.EURO:
            deck_price += card_data.latest_eur_price * count if card_data and card_data.latest_eur_price else 0.0
        elif currency == CardCurrency.US_DOLLAR:
            deck_price += card_data.latest_usd_price * count if card_data and card_data.latest_usd_price else 0.0
        else:
            raise NotImplementedError
    return deck_price
