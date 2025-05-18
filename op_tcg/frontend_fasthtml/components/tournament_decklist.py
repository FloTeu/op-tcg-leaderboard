from fasthtml import ft
from collections import Counter
from typing import Dict

from op_tcg.backend.models.cards import Card, OPTcgCardCatagory

def create_decklist_view(decklist: Dict[str, int], cid2card_data: Dict[str, Card], title: str = "Decklist"):
    """
    Create a view of a decklist showing each card and its occurrence count in a grid layout.
    Mobile view shows 1 card per row, desktop shows up to 6 cards per row.
    
    Args:
        decklist: Dictionary mapping card IDs to their count
        cid2card_data: Dictionary mapping card IDs to their data
        title: Title for the decklist section
    """
    # Group cards by their type
    card_types = {
        OPTcgCardCatagory.LEADER: [],
        OPTcgCardCatagory.CHARACTER: [],
        OPTcgCardCatagory.EVENT: [],
        OPTcgCardCatagory.STAGE: []
    }
    
    # Sort cards into their types
    for card_id, count in decklist.items():
        if card_id in cid2card_data:
            card = cid2card_data[card_id]
            card_type = card.card_category
            if card_type in card_types:
                card_types[card_type].append((card, count))
    
    # Sort cards within each type by name
    for type_cards in card_types.values():
        type_cards.sort(key=lambda x: x[0].name)
    
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
                                cls="w-full h-auto rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-200"
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