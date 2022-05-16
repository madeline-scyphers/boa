import json
import click
from pathlib import Path

from numpy.random import default_rng

from optiwrap import get_synth_func


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
@click.option(
    "-fn",
    "--function",
    type=str,
    default="hartmann6",
    help="name of synthetic function",
)
@click.argument("xs", nargs=-1, type=click.FLOAT)
def main(output_dir: Path, input_size, standard_dev, function, xs):
    synthetic_func = get_synth_func(function)
    rng = default_rng()
    X = rng.normal(loc=xs, scale=standard_dev, size=(input_size, len(xs)))
    results = dict(input=X.tolist(), output=synthetic_func(X).tolist(), metric_name=function)
    with open(output_dir / "output.json", "w") as outfile:
        json.dump(results, outfile, indent=4)
    print(f"saved results: {results} to {output_dir / 'output.json'}")


if __name__ == "__main__":
    main()
