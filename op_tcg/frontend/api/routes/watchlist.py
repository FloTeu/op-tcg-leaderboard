from starlette.requests import Request
from starlette.responses import JSONResponse
from op_tcg.backend.db import add_to_watchlist, remove_from_watchlist

def setup_watchlist_routes(rt):

    @rt("/api/watchlist/add", methods=["POST"])
    async def add_watchlist(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        try:
            data = await request.json()
        except:
             return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        card_id = data.get('card_id')
        card_version = data.get('card_version', 'Base')
        language = data.get('language', 'English')

        if not card_id:
            return JSONResponse({"error": "Missing card_id"}, status_code=400)

        user_id = user.get('sub')
        add_to_watchlist(user_id, card_id, card_version, language)

        return JSONResponse({"status": "success", "message": "Card added to watchlist"})

    @rt("/api/watchlist/remove", methods=["POST"])
    async def remove_watchlist(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        try:
            data = await request.json()
        except:
             return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        card_id = data.get('card_id')
        card_version = data.get('card_version', 0)
        language = data.get('language', 'en')

        # Map 'Base' to 0 for compatibility
        if card_version == 'Base':
            card_version = 0

        if not card_id:
            return JSONResponse({"error": "Missing card_id"}, status_code=400)

        user_id = user.get('sub')
        remove_from_watchlist(user_id, card_id, card_version, language)

        return JSONResponse({"status": "success", "message": "Card removed from watchlist"})

