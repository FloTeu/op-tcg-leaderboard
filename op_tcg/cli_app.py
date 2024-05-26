import click
from op_tcg.cli.crawling import crawling_group
from op_tcg.cli.etl import etl_group
from op_tcg.frontend.cli import frontend_group
from dotenv import load_dotenv

load_dotenv()

@click.group()
def app() -> None:
    """
    Define a click app
    """
    pass



app.add_command(crawling_group)
app.add_command(etl_group)
app.add_command(frontend_group)

if __name__ == "__main__":
    app()
