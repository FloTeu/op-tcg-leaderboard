from fasthtml import ft
from collections import Counter
from typing import Dict

from op_tcg.backend.etl.extract import get_card_image_url
from op_tcg.backend.models.cards import Card, OPTcgCardCatagory, CardCurrency, OPTcgLanguage
from op_tcg.backend.models.input import MetaFormat

def create_decklist_view(decklist: Dict[str, int], cid2card_data: Dict[str, Card], title: str = "Decklist", meta_format: MetaFormat = None, currency: CardCurrency = CardCurrency.EURO):
    """
    Create a view of a decklist showing each card and its occurrence count in a grid layout.
    Mobile view shows 1 card per row, desktop shows up to 6 cards per row.
    
    Args:
        decklist: Dictionary mapping card IDs to their count
        cid2card_data: Dictionary mapping card IDs to their data
        title: Title for the decklist section
        meta_format: Meta format for card popularity data
        currency: Currency for price display
    """
    # Group cards by their type
    card_types = {
        OPTcgCardCatagory.LEADER: [],
        OPTcgCardCatagory.CHARACTER: [],
        OPTcgCardCatagory.EVENT: [],
        OPTcgCardCatagory.STAGE: [],
        "Unknown": []
    }
    
    # Sort cards into their types
    for card_id, count in decklist.items():
        if card_id in cid2card_data:
            card = cid2card_data[card_id]
            card_type = card.card_category
            if card_type in card_types:
                card_types[card_type].append((card, count))
        else:
            card = Card.from_default()
            card.name = "Unknown"
            card.id = card_id
            card.image_url = get_card_image_url(card_id, OPTcgLanguage.JP)
            card_types["Unknown"].append((card, count))
    
    # Sort cards within each type by color and cost
    for type_cards in card_types.values():
        type_cards.sort(key=lambda x: (x[0].colors, x[0].cost))
    
    # Get all card IDs for the modal navigation
    all_card_ids = [card_id for card_id in decklist.keys() if card_id in cid2card_data]
    card_elements_param = '&card_elements='.join(all_card_ids)
    
    # Use latest meta format if none provided
    if meta_format is None:
        meta_format = MetaFormat.latest_meta_format()
    
    # Create the decklist view
    decklist_sections = []
    for card_type, cards in card_types.items():
        if cards:  # Only show sections with cards
            card_elements = []
            for card, count in cards:
                card_elements.append(
                    ft.Div(
                        ft.Div(
                            ft.Img(
                                src=card.image_url,
                                cls="w-full h-auto rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-200 cursor-pointer hover:opacity-90 transition-opacity",
                                hx_get=f"/api/card-modal?card_id={card.id}&card_elements={card_elements_param}&meta_format={meta_format}&currency={currency}",
                                hx_target="body",
                                hx_swap="beforeend"
                            ),
                            cls="relative aspect-[2.5/3.5] overflow-hidden max-w-[200px] mx-auto"
                        ),
                        ft.Div(
                            ft.Div(
                                ft.Span(card.name, cls="font-semibold text-sm"),
                                ft.Span(f" × {count}", cls="text-gray-400"),
                                cls="text-white text-center"
                            ),
                            cls="mt-2"
                        ),
                        cls="transform hover:scale-105 transition-transform duration-200"
                    )
                )
            
            decklist_sections.append(
                ft.Div(
                    ft.H3(card_type, cls="text-lg font-bold text-white mb-4"),
                    ft.Div(
                        *card_elements,
                        cls="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-6"
                    ),
                    cls="mb-8"
                )
            )
    
    return ft.Div(
        ft.H2(title, cls="text-2xl font-bold text-white mb-6"),
        *decklist_sections,
        cls="bg-gray-900 rounded-lg p-6 shadow-lg"
    ) 