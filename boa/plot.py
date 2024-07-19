"""
###################################
Plotting & EDA CLI
###################################

You can launch a basic EDA plot dashboard view
of your optimization with::

    boa.plot path/to/scheduler.json
    or
    python -m boa.plot path/to/scheduler.json


"""


import pathlib

import click
import panel as pn

import boa.plotting
from boa.plotting import app_view


@click.command(
    epilog=f"Name of Plots to be added here: {', '.join(plot for plot in boa.plotting.__all__ if plot != 'app_view')}"
)
@click.option(
    "-sp",
    "--scheduler-path",
    type=click.Path(),
    default="",
    help="Path to scheduler json file.",
)
def main(scheduler_path):
    """
    Launch a basic EDA plot view of your optimization.
    Creating a web app with the scheduler json file.

    """
    template = app_view(scheduler=scheduler_path)
    pn.serve({pathlib.Path(__file__).name: template})


if __name__ == "__main__":
    main()
