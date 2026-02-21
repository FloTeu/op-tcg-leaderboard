from google.cloud import firestore
from op_tcg.backend.models.cards import OPTcgLanguage

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
        'last_login': firestore.SERVER_TIMESTAMP
    }

    # Use merge=True to update fields without overwriting the entire document
    db.collection('users').document(user_id).set(data, merge=True)

def add_to_watchlist(user_id: str, card_id: str, card_version: int = 0, language: OPTcgLanguage = OPTcgLanguage.EN):
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
        'added_at': firestore.SERVER_TIMESTAMP
    })

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
