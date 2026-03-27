import secrets


def get_csrf_token(session: dict) -> str:
    """Return the session CSRF token, generating one if absent."""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def validate_csrf_token(session: dict, token: str | None) -> bool:
    expected = session.get('csrf_token')
    if not expected or not token:
        return False
    return secrets.compare_digest(expected, token)