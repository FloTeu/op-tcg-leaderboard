from fasthtml import ft
from starlette.requests import Request

from op_tcg.backend.etl.extract import get_card_image_url
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams
from op_tcg.frontend_fasthtml.utils.similar import get_most_similar_leader_data, SimilarLeaderData
from op_tcg.frontend_fasthtml.utils.leader_data import lid_to_name_and_lid, get_lid2ldata_dict_cached
from op_tcg.frontend_fasthtml.utils.extract import get_card_id_card_data_lookup
from op_tcg.backend.models.cards import Card, LatestCardPrice, OPTcgLanguage

SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def setup_api_routes(rt):
    @rt("/api/leader-similar")
    async def get_leader_similar(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        
        # Get similar leader data
        lid2similar_leader_data: dict[str, SimilarLeaderData] = get_most_similar_leader_data(
            params.lid,
            params.meta_format,
            threshold_occurrence=0.1
        )
        
        if not lid2similar_leader_data:
            return ft.P("No similar leaders found.", cls="text-red-400")
            
        # Get card data lookup
        cid2cdata_dict = get_card_id_card_data_lookup()
        lid2data_dict = get_lid2ldata_dict_cached()
        
        # Sort by similarity score
        most_similar_leader_ids = sorted(
            lid2similar_leader_data,
            key=lambda k: lid2similar_leader_data[k].similarity_score,
            reverse=True
        )
        
        # Get the selected similar leader ID from the request or use the most similar one
        selected_most_similar_lid = params.similar_lid if params.similar_lid in most_similar_leader_ids else most_similar_leader_ids[0]
        similar_leader_data = lid2similar_leader_data[selected_most_similar_lid]
        
        # Calculate prices
        cards_missing_price_eur = sum([
            cid2cdata_dict.get(cid, LatestCardPrice.from_default()).latest_eur_price *
            similar_leader_data.card_id2avg_count_card[cid]
            for cid in similar_leader_data.cards_missing
        ])
        cards_missing_price_usd = sum([
            cid2cdata_dict.get(cid, LatestCardPrice.from_default()).latest_usd_price *
            similar_leader_data.card_id2avg_count_card[cid]
            for cid in similar_leader_data.cards_missing
        ])
        
        cards_intersection_price_eur = sum([
            cid2cdata_dict.get(cid, LatestCardPrice.from_default()).latest_eur_price *
            similar_leader_data.card_id2avg_count_card[cid]
            for cid in similar_leader_data.cards_intersection
        ])
        cards_intersection_price_usd = sum([
            cid2cdata_dict.get(cid, LatestCardPrice.from_default()).latest_usd_price *
            similar_leader_data.card_id2avg_count_card[cid]
            for cid in similar_leader_data.cards_intersection
        ])
        
        # Create the component
        return ft.Div(
            ft.H2("Most Similar Leader", cls="text-2xl font-bold text-white mb-4"),
            
            # Leader select wrapper
            ft.Div(
                ft.Label("Similar Leader", cls="text-white font-medium block mb-2"),
                ft.Select(
                    id="similar-leader-select",
                    name="similar_lid",
                    cls=SELECT_CLS + " styled-select",
                    *[
                        ft.Option(
                            f"{lid2data_dict.get(lid, Card.from_default()).name} ({lid}) - {int(lid2similar_leader_data[lid].similarity_score * 100)}% similar",
                            value=lid,
                            selected=(lid == selected_most_similar_lid)
                        ) 
                        for lid in most_similar_leader_ids[:10]  # Show top 10 similar leaders
                    ],
                    hx_get="/api/leader-similar",
                    hx_trigger="change",
                    hx_target="#leader-similar-container",
                    hx_include="[name='meta_format'],[name='lid'],[name='only_official'],[name='similar_lid'],[name='region']"
                ),
                cls="relative mb-4"  # Required for proper styling
            ),
            
            # Image and Stats container
            ft.Div(
                # Leader image with link
                ft.Div(
                    ft.A(
                        ft.Img(
                            src=lid2data_dict[selected_most_similar_lid].aa_image_url,
                            cls="w-full rounded-lg shadow-lg"
                        ),
                        href=f"/leader?lid={selected_most_similar_lid}",
                        cls="block"
                    ),
                    cls="w-full md:w-1/2"
                ),
                
                # Stats
                ft.Div(
                    ft.P(f"Deck Similarity: {int(round(similar_leader_data.similarity_score, 2) * 100)}%", 
                         cls="text-blue-400"),
                    ft.P(f"Missing Cards Price: {round(cards_missing_price_eur, 2)}€ | ${round(cards_missing_price_usd, 2)}", 
                         cls="text-red-400"),
                    ft.P(f"Intersection Cards Price: {round(cards_intersection_price_eur, 2)}€ | ${round(cards_intersection_price_usd, 2)}", 
                         cls="text-green-400"),
                    cls="w-full md:w-1/2 md:pl-4 mt-4 md:mt-0 bg-gray-700 rounded-lg p-4 md:ml-4"
                ),
                cls="flex flex-col md:flex-row items-start mb-4"
            ),
            
            # Cards sections
            ft.Details(
                ft.Summary("Cards in both decks", cls="text-xl font-bold text-white mb-2 cursor-pointer outline-none focus:ring-2 focus:ring-blue-500 rounded"),
                ft.Div(
                    *[
                        ft.Img(
                            src=cid2cdata_dict[cid].image_url if cid in cid2cdata_dict else get_card_image_url(cid, language=OPTcgLanguage.JP),
                            cls="w-1/4 inline-block p-1"
                        ) for cid in similar_leader_data.cards_intersection
                    ],
                    cls="flex flex-wrap pt-2"  # Add some padding when expanded
                ),
                # open=True, # Uncomment to make it open by default
                cls="mb-4 bg-gray-750 p-3 rounded-lg shadow"
            ),
            
            ft.Details(
                ft.Summary("Missing cards", cls="text-xl font-bold text-white mb-2 cursor-pointer outline-none focus:ring-2 focus:ring-blue-500 rounded"),
                ft.Div(
                    *[
                        ft.Img(
                            src=cid2cdata_dict[cid].image_url if cid in cid2cdata_dict else get_card_image_url(cid, language=OPTcgLanguage.JP),
                            cls="w-1/4 inline-block p-1"
                        ) for cid in similar_leader_data.cards_missing
                    ],
                    cls="flex flex-wrap pt-2"  # Add some padding when expanded
                ),
                # open=True, # Uncomment to make it open by default
                cls="mb-4 bg-gray-750 p-3 rounded-lg shadow"
            ),
            
            cls="bg-gray-800 rounded-lg p-6 shadow-xl"
        ) 