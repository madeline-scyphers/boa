# TODO: Move this to a docs only feature and move back to PYYAML
import pathlib  # pragma: no cover

import click  # pragma: no cover
from ruamel.yaml import YAML  # pragma: no cover
from ruamel.yaml.compat import StringIO  # pragma: no cover

from boa.config.config import (  # pragma: no cover
    add_comment_recurse,
    generate_default_doc_config,
)


class YAMLDumper(YAML):  # pragma: no cover
    def dump(self, data, stream=None, **kw):
        inefficient = False
        if stream is None:
            inefficient = True
            stream = StringIO()
        YAML.dump(self, data, stream, **kw)
        if inefficient:
            return stream.getvalue()


@click.command()  # pragma: no cover
@click.option(  # pragma: no cover
    "--output-path",
    "-o",
    type=click.Path(exists=False, file_okay=True, dir_okay=False, path_type=pathlib.Path),
    default="default_config.yaml",
)
def main(output_path):  # pragma: no cover
    """Generate a default config file with comments."""
    d, c = generate_default_doc_config()
    yaml = YAML()
    data = yaml.load(YAMLDumper().dump(d))
    data = add_comment_recurse(data, c)
    with open(pathlib.Path(output_path), "w") as f:
        yaml.dump(data, f)


if __name__ == "__main__":  # pragma: no cover
    main()
