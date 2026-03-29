from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

# efficient: Load config once
# Config will read from environment variables directly if .env file is not found or config file not specified
config = Config('.env')
oauth = OAuth(config)

# Register a provider (e.g., Google)
# Green Coding: OAuth offloads authentication computation to the provider
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

