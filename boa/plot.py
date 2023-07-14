"""
BOA plotting CLI module

You can launch a basic EDA plot view
of your optimization with::

    python -m boa.plot path/to/scheduler.json


"""


import pathlib

import click
import panel as pn

from boa.plotting import app_view


@click.command()
@click.option(
    "-sp",
    "--scheduler-path",
    type=click.Path(),
    default="",
    help="Path to scheduler json file.",
)
def main(scheduler_path):
    template = app_view(scheduler=scheduler_path)
    pn.serve({pathlib.Path(__file__).name: template})


if __name__ == "__main__":
    main()
