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
    if st.runtime.exists():
        # The app has been executed with `streamlit run app.py`
        main()
    else:
        # If the file has been executed with python (`python app.py`), the streamlit functionality
        # won't work. This line reruns the app within the streamlit context, as if it has been
        # executed with `streamlit run app.py`.
        # This is necessary when installing this project from a .whl package, since the executable
        # only gets execute by python and not by streamlit.
        st_bootstrap.run(
            __file__,
            is_hello=False,
            args=[],
            flag_options={},
        )

if __name__ == "__main__":
    start()
