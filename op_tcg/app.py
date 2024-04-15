import click
from op_tcg.cli.crawling import crawling_group


@click.group()
def app() -> None:
    """
    Define a click app
    """

app.add_command(crawling_group)

if __name__ == "__main__":
    app()
