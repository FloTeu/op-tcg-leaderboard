from fasthtml import ft
from starlette.requests import Request

from op_tcg.backend.etl.extract import get_card_image_url
from op_tcg.frontend.utils.api import get_query_params_as_dict
from op_tcg.frontend.api.models import LeaderDataParams
from op_tcg.frontend.utils.similar import get_most_similar_leader_data, SimilarLeaderData
from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid, get_lid2ldata_dict_cached
from op_tcg.frontend.utils.extract import get_card_id_card_data_lookup
from op_tcg.backend.models.cards import Card, LatestCardPrice, OPTcgLanguage

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
        
        leader_url = f"/leader?lid={selected_most_similar_lid}{''.join([f'&meta_format={mf}' for mf in params.meta_format])}{f'&region={params.region}' if params.region else ''}"

        # Create the component
        return ft.Div(
            ft.H2("Most Similar Leader", cls="lp-display mb-4", style="font-size:1.4rem; color:#f1f5f9;"),

            # Leader select
            ft.Div(
                ft.Label("Similar Leader", cls="lp-section-label"),
                ft.Select(
                    id="similar-leader-select",
                    name="similar_lid",
                    cls="lp-select styled-select",
                    *[
                        ft.Option(
                            f"{lid2data_dict.get(lid, Card.from_default()).name} ({lid}) - {int(lid2similar_leader_data[lid].similarity_score * 100)}% similar",
                            value=lid,
                            selected=(lid == selected_most_similar_lid)
                        )
                        for lid in most_similar_leader_ids[:10]
                    ],
                    hx_get="/api/leader-similar",
                    hx_trigger="change",
                    hx_target="#leader-similar-container",
                    hx_include="[name='meta_format'],[name='lid'],[name='only_official'],[name='similar_lid'],[name='region']"
                ),
                cls="mb-4"
            ),

            # Image + Stats
            ft.Div(
                ft.Div(
                    ft.A(
                        ft.Img(src=lid2data_dict[selected_most_similar_lid].aa_image_url, cls="w-full rounded-lg"),
                        href=leader_url, cls="block"
                    ),
                    cls="w-full md:w-1/2"
                ),
                ft.Div(
                    ft.Div(
                        ft.Span("Similarity", cls="lp-section-label"),
                        ft.Span(f"{int(round(similar_leader_data.similarity_score, 2) * 100)}%", cls="lp-mono", style="font-size:1.1rem; color:#38bdf8; font-weight:700;"),
                        cls="flex flex-col mb-3"
                    ),
                    ft.Div(
                        ft.Span("Missing Cards", cls="lp-section-label"),
                        ft.Span(f"{round(cards_missing_price_eur, 2)}€ / ${round(cards_missing_price_usd, 2)}", cls="lp-mono", style="font-size:0.85rem; color:#ef4444;"),
                        cls="flex flex-col mb-3"
                    ),
                    ft.Div(
                        ft.Span("Shared Cards", cls="lp-section-label"),
                        ft.Span(f"{round(cards_intersection_price_eur, 2)}€ / ${round(cards_intersection_price_usd, 2)}", cls="lp-mono", style="font-size:0.85rem; color:#10b981;"),
                        cls="flex flex-col"
                    ),
                    cls="w-full md:w-1/2 md:pl-4 mt-4 md:mt-0 p-4 rounded-lg",
                    style="background:#080e1c; border:1px solid #1a2540;"
                ),
                cls="flex flex-col md:flex-row items-start mb-4"
            ),

            # Cards sections
            ft.Details(
                ft.Summary("Cards in both decks", cls="lp-display cursor-pointer mb-2", style="font-size:0.95rem; color:#94a3b8; letter-spacing:0.08em;"),
                ft.Div(
                    *[
                        ft.Img(
                            src=cid2cdata_dict[cid].image_url if cid in cid2cdata_dict else get_card_image_url(cid, language=OPTcgLanguage.JP),
                            cls="w-1/4 inline-block p-1"
                        ) for cid in similar_leader_data.cards_intersection
                    ],
                    cls="flex flex-wrap pt-2"
                ),
                cls="mb-3 p-3 rounded-lg", style="background:#080e1c; border:1px solid #1a2540;"
            ),

            ft.Details(
                ft.Summary("Missing cards", cls="lp-display cursor-pointer mb-2", style="font-size:0.95rem; color:#94a3b8; letter-spacing:0.08em;"),
                ft.Div(
                    *[
                        ft.Img(
                            src=cid2cdata_dict[cid].image_url if cid in cid2cdata_dict else get_card_image_url(cid, language=OPTcgLanguage.JP),
                            cls="w-1/4 inline-block p-1"
                        ) for cid in similar_leader_data.cards_missing
                    ],
                    cls="flex flex-wrap pt-2"
                ),
                cls="mb-3 p-3 rounded-lg", style="background:#080e1c; border:1px solid #1a2540;"
            ),
        ) 