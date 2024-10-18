import subprocess
import os
import sys
from pathlib import Path


def build_st_elements_frontend(dep_path: Path | str | None = None):
    current_dir = os.getcwd()
    if dep_path:
        streamlit_elements_path = Path(dep_path) / "streamlit_elements"
    else:
        import streamlit as st
        streamlit_elements_path = Path(st.__path__[0]).parent / "streamlit_elements"

    # Change to the frontend directory
    os.chdir(f'{streamlit_elements_path}/frontend')

    # Install npm dependencies
    subprocess.run(['npm', 'install'], check=True)

    # Build the frontend
    subprocess.run(['npm', 'run', 'build'], check=True)

    # Change dir back to previous one
    os.chdir(current_dir)


def build_nivo_chart_frontend():
    current_dir = os.getcwd()
    # Change to the frontend directory
    os.chdir(f'components/nivo_charts/nivo_charts/frontend')

    # Install npm dependencies
    subprocess.run(['npm', 'install'], check=True)

    # Build the frontend
    subprocess.run(['npm', 'run', 'build'], check=True)

    # Change dir back to previous one
    os.chdir(current_dir)

def build_frontend(dep_path=None):
    build_st_elements_frontend(dep_path)
    build_nivo_chart_frontend()

if __name__ == "__main__":
    # Get the dependency path from command-line arguments
    dep_path = sys.argv[1] if len(sys.argv) > 1 else None
    build_frontend(dep_path)
