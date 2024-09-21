import subprocess
import os

def build_st_elements_frontend():
    import streamlit_elements
    current_dir = os.getcwd()
    streamlit_elements_path = streamlit_elements.__path__[0]
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

def build_frontend():
    build_st_elements_frontend()
    build_nivo_chart_frontend()
