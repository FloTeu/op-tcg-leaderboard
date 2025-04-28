from op_tcg.backend.models.cards import LatestCardPrice, CardCurrency


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
