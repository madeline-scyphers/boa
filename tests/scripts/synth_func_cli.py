import json
import click
from pathlib import Path

from numpy.random import default_rng
from ax.utils.measurement.synthetic_functions import hartmann6


@click.command()
@click.option(
    "-op", "--output_dir",
    type=click.Path(path_type=Path),
    help="Path for where to save output to",
)
@click.option(
    "-n", "--input_size",
    type=int,
    default=10,
    help="number of inputs to generate",
)
@click.option(
    "-sd", "--standard_dev",
    type=float,
    default=.1,
    help="standard deviation of generated data",
)
@click.argument('xs', nargs=6, type=float)
def main(output_dir: Path, input_size, standard_dev, xs):
    rng = default_rng()
    X = rng.normal(loc=xs, scale=standard_dev, size=(input_size, len(xs)))
    results = dict(input=X.tolist(),
                   output=hartmann6(X).tolist(),
                   metric_name="hartmann6")
    with open(output_dir / "output.json", "w") as outfile:
        json.dump(results, outfile, indent=4)
    print(f"saved results: {results} to {output_dir / 'output.json'}")


if __name__ == "__main__":
    main()
