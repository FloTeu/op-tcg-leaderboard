import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    # Check if required environment variables are set
    if not os.environ.get("GCP_CREDENTIALS"):
        # For development/demo purposes, you might want to set a default path
        # or handle this case differently
        print("Warning: GCP_CREDENTIALS environment variable not set")
        
    from op_tcg.frontend_fasthtml.main import app
    
    # This is the entry point for Vercel
    # Vercel expects the ASGI app to be available as a variable
    # FastHTML apps are ASGI compatible
    handler = app
    
except Exception as e:
    print(f"Error importing application: {e}")
    # Create a simple fallback app for debugging
    from fasthtml.common import fast_app, Div, H1, P
    
    fallback_app, rt = fast_app()
    
    @rt("/")
    def home():
        return Div(
            H1("OP TCG Leaderboard"),
            P(f"Application failed to start: {str(e)}"),
            P("Please check your environment configuration.")
        )
    
    handler = fallback_app 