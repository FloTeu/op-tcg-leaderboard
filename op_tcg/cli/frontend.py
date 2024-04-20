import os

import click
import streamlit as st
import streamlit.web.bootstrap as st_bootstrap
from op_tcg.frontend.app import main


@click.group("frontend", help="Frontend functionality")
def frontend_group() -> None:
    """
    Define a click group for the frontend section
    """
    pass


@frontend_group.command()
def start(
) -> None:
    # expects working directory to be the root of the project
    os.system("streamlit run op_tcg/frontend/app.py")


if __name__ == "__main__":
    start()
