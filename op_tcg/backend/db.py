from google.cloud import firestore

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

    # Update or create user document
    db.collection('users').document(user_id).set(data, merge=True)

