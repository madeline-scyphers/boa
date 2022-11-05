import json
from pathlib import Path

import click
import numpy as np

import boa


@click.command()
@click.option(
    "-op",
    "--output_dir",
    type=click.Path(path_type=Path),
    help="Path for where to save output to",
)
@click.option(
    "-n",
    "--input_size",
    type=int,
    default=10,
    help="number of inputs to generate",
)
@click.option(
    "-sd",
    "--standard_dev",
    type=float,
    default=0.1,
    help="standard deviation of generated data",
)
@click.argument("xs", nargs=-1, type=click.FLOAT)
def main(output_dir: Path, input_size, standard_dev, xs):
    """"""