# entrypoint.py
import subprocess

def build_frontend():
    # Build frontend
    subprocess.run(['poetry', 'run', 'build-frontend'], check=True)

def run_streamlit():
    # Run the Streamlit app
    subprocess.run(['streamlit', 'run', 'op_tcg/frontend/Leaderboard.py'])

if __name__ == "__main__":
    build_frontend()
    run_streamlit()
