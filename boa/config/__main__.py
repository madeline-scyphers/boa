import pathlib

import click
from ruamel.yaml import YAML
from ruamel.yaml.compat import StringIO

from boa.config.config import add_comment_recurse, generate_default_doc_config


class YAMLDumper(YAML):
    def dump(self, data, stream=None, **kw):
        inefficient = False
        if stream is None:
            inefficient = True
            stream = StringIO()
        YAML.dump(self, data, stream, **kw)
        if inefficient:
            return stream.getvalue()


@click.command()
@click.option(
    "--output-path",
    "-o",
    type=click.Path(exists=False, file_okay=True, dir_okay=False, path_type=pathlib.Path),
    default="default_config.yaml",
)
def main(output_path):
    """Generate a default config file with comments."""
    d, c = generate_default_doc_config()
    yaml = YAML()
    data = yaml.load(YAMLDumper().dump(d))
    data = add_comment_recurse(data, c)
    with open(pathlib.Path(output_path), "w") as f:
        yaml.dump(data, f)


if __name__ == "__main__":
    main()
