import json
from pathlib import Path

import click
import numpy as np

import boa
from boa.logger import get_logger

logger = get_logger()


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
    # sets rng seed and gets rng Generator class, numpy recommended way to do random numbers
    rng = np.random.default_rng()
    synthetic_func = boa.get_synth_func("branin")
    X = rng.normal(loc=xs, scale=standard_dev, size=(input_size, len(xs)))
    results = dict(input=X.tolist(), output=synthetic_func(X).tolist(), metric_name="branin")
    with open(output_dir / "output.json", "w") as outfile:
        json.dump(results, outfile, indent=4)


if __name__ == "__main__":
    main()
