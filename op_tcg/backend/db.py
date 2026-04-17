from google.cloud import firestore
from op_tcg.backend.models.cards import OPTcgLanguage, CardCurrency
from op_tcg.backend.models.input import MetaFormatRegion

DEFAULT_WATCHLIST_TAG = "my collection"

# Initialize Firestore
# Using a singleton pattern to avoid re-initializing the client
_db = None

def get_db():
    global _db
    if _db is None:
        # Check if running in a cloud function or local environment
        # Usually environment variables handle credentials
        try:
            _db = firestore.Client(database="op-leaderboard")
        except Exception as e:
            print(f"Warning: Firestore client initialization failed: {e}")
            return None
    return _db

def get_user(user_id: str):
    """
    Fetches user data efficiently.
    """
    db = get_db()
    if not db:
        return None

    doc = db.collection('users').document(user_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

def update_user_login(user_info: dict):
    """
    Updates user login information in Firestore.
    """
    db = get_db()
    if not db:
        return

    user_id = user_info.get('sub')
    if not user_id:
        return

    # Prepare data to store
    # Green coding: Only store essential data
    data = {
        'id': user_id,
        'name': user_info.get('name'),
        'picture': user_info.get('picture'),
        'email': user_info.get('email'),
        'provider': user_info.get('provider'),
        'last_login': firestore.SERVER_TIMESTAMP
    }

    # Use merge=True to update fields without overwriting the entire document
    db.collection('users').document(user_id).set(data, merge=True)

def add_to_watchlist(user_id: str, card_id: str, card_version: int = 0, language: OPTcgLanguage = OPTcgLanguage.EN, tags: list = None):
    """
    Adds a card to the user's watchlist efficiently.
    """
    db = get_db()
    if not db:
        return

    # Use a subcollection for scalable watchlist storage
    # avoids hitting document size limits if user tracks many cards
    watchlist_ref = db.collection('users').document(user_id).collection('watchlist')

    # Store minimal data, use composite key as document ID for uniqueness
    doc_id = f"{card_id}_{card_version}_{language}"
    watchlist_ref.document(doc_id).set({
        'card_id': card_id,
        'card_version': card_version,
        'language': language,
        'quantity': 1,
        'tags': tags if tags is not None else [DEFAULT_WATCHLIST_TAG],
        'added_at': firestore.SERVER_TIMESTAMP
    })

def update_watchlist_quantity(user_id: str, card_id: str, card_version: int = 0, language: OPTcgLanguage = OPTcgLanguage.EN, quantity: int = 1):
    """Updates the quantity of a card in the user's watchlist."""
    db = get_db()
    if not db:
        return
    doc_id = f"{card_id}_{card_version}_{language}"
    db.collection('users').document(user_id).collection('watchlist').document(doc_id).update(
        {'quantity': max(1, quantity)}
    )


def update_watchlist_tags(user_id: str, card_id: str, card_version: int = 0, language: OPTcgLanguage = OPTcgLanguage.EN, tags: list = None):
    """Updates the tags of an existing watchlist item."""
    db = get_db()
    if not db:
        return
    doc_id = f"{card_id}_{card_version}_{language}"
    db.collection('users').document(user_id).collection('watchlist').document(doc_id).update(
        {'tags': tags or [DEFAULT_WATCHLIST_TAG]}
    )

def remove_from_watchlist(user_id: str, card_id: str, card_version: int  = 0, language: OPTcgLanguage = OPTcgLanguage.EN):
    """
    Removes a card from the user's watchlist.
    """
    db = get_db()
    if not db:
        return

    watchlist_ref = db.collection('users').document(user_id).collection('watchlist')
    doc_id = f"{card_id}_{card_version}_{language}"
    watchlist_ref.document(doc_id).delete()

def get_watchlist(user_id: str):
    """
    Retrieves the user's watchlist.
    """
    db = get_db()
    if not db:
        return []

    watchlist_ref = db.collection('users').document(user_id).collection('watchlist')
    # Use stream() for memory efficiency with large result sets
    docs = watchlist_ref.stream()

    return [doc.to_dict() for doc in docs]


def get_user_settings(user_id: str) -> dict:
    """Retrieves persisted user settings, returns defaults if not set."""
    user = get_user(user_id)
    defaults = {"currency": CardCurrency.EURO.value, "region": MetaFormatRegion.ALL.value}
    if not user:
        return defaults
    return {**defaults, **user.get("settings", {})}


def update_user_settings(user_id: str, settings: dict):
    """Persists user settings (currency, region) in the user document."""
    db = get_db()
    if not db:
        return
    db.collection('users').document(user_id).set({"settings": settings}, merge=True)


def _decklist_doc_id(leader_id: str, tournament_id: str, player_id: str) -> str:
    """Build a safe Firestore document ID for a decklist watchlist entry."""
    import re
    raw = f"{leader_id}__{tournament_id}__{player_id}"
    # Firestore doc IDs must not contain '/' and must not be '..' or '.'.
    # Replace any character that isn't alphanumeric, dash, or underscore.
    return re.sub(r'[^a-zA-Z0-9\-_]', '_', raw)[:400]


def add_decklist_to_watchlist(user_id: str, leader_id: str, tournament_id: str, player_id: str, meta_format: str = "", tags: list = None):
    """Adds a decklist to the user's decklist watchlist."""
    db = get_db()
    if not db:
        return
    ref = db.collection('users').document(user_id).collection('decklist_watchlist')
    doc_id = _decklist_doc_id(leader_id, tournament_id, player_id)
    ref.document(doc_id).set({
        'leader_id': leader_id,
        'tournament_id': tournament_id,
        'player_id': player_id,
        'meta_format': meta_format,
        'tags': tags if tags is not None else [DEFAULT_WATCHLIST_TAG],
        'added_at': firestore.SERVER_TIMESTAMP
    })


def remove_decklist_from_watchlist(user_id: str, leader_id: str, tournament_id: str, player_id: str):
    """Removes a decklist from the user's decklist watchlist."""
    db = get_db()
    if not db:
        return
    doc_id = _decklist_doc_id(leader_id, tournament_id, player_id)
    db.collection('users').document(user_id).collection('decklist_watchlist').document(doc_id).delete()


def update_decklist_watchlist_tags(user_id: str, leader_id: str, tournament_id: str, player_id: str, tags: list = None):
    """Updates the tags of a decklist watchlist entry."""
    db = get_db()
    if not db:
        return
    doc_id = _decklist_doc_id(leader_id, tournament_id, player_id)
    db.collection('users').document(user_id).collection('decklist_watchlist').document(doc_id).update(
        {'tags': tags or [DEFAULT_WATCHLIST_TAG]}
    )


def get_decklist_watchlist(user_id: str) -> list[dict]:
    """Retrieves the user's decklist watchlist."""
    db = get_db()
    if not db:
        return []
    ref = db.collection('users').document(user_id).collection('decklist_watchlist')
    return [doc.to_dict() for doc in ref.stream()]


def delete_user(user_id: str):
    """Deletes a user's watchlist subcollection and user document."""
    db = get_db()
    if not db:
        return
    # Delete all watchlist docs first (subcollections must be removed manually)
    watchlist_ref = db.collection('users').document(user_id).collection('watchlist')
    for doc in watchlist_ref.stream():
        doc.reference.delete()
    db.collection('users').document(user_id).delete()
