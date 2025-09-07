import os
import sys
from pathlib import Path
from fasthtml import serve

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    # Check if required environment variables are set
    if not os.environ.get("GOOGLE_SERVICE_KEY"):
        print("Warning: GOOGLE_SERVICE_KEY environment variable not set")
        
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        print("Warning: GOOGLE_CLOUD_PROJECT environment variable not set")
        
    from op_tcg.frontend_fasthtml.main import app
    
    # This is the entry point for Vercel
    # Vercel expects the ASGI app to be available as a variable
    # FastHTML apps are ASGI compatible
    
except Exception as e:
    print(f"Error importing application: {e}")
    # Create a simple fallback app for debugging
    from fasthtml.common import fast_app, Div, H1, P
    
    app, rt = fast_app()
    
    @rt("/")
    def home():
        return Div(
            H1("OP TCG Leaderboard"),
            P(f"Application failed to start: {str(e)}"),
            P("Please check your environment configuration."),
            P("Required environment variables:"),
            P("- GOOGLE_SERVICE_KEY (base64 encoded service account JSON)"),
            P("- GOOGLE_CLOUD_PROJECT (your GCP project ID)")
        )

serve()