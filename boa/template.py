from __future__ import annotations

import importlib
import pathlib
from enum import Enum
from typing import Optional

import jinja2


class JinjaTemplateVars(Enum):
    """These are the variables that are passed to the jinja2 template.
    They should always be able to be used in your template (config file)."""

    config_path = "Full path to the config file."
    config_dir_name = "Name of the directory containing the config file."
    config_file_name = "Name of the config file."


def render_template_from_path(path, template_kw: Optional[dict] = None, **kwargs):
    """
    Render a template from a path.

    Parameters
    ----------
    path : Path
        Path to the template file.
    template_kw : dict, optional
        Dictionary of keyword arguments to pass to the jinja2.Template constructor.
    **kwargs
        Keyword arguments to pass to the template as variables to render.
    """
    path = pathlib.Path(path)
    with open(path) as f:
        kw = {
            JinjaTemplateVars.config_path.name: path,
            JinjaTemplateVars.config_dir_name.name: path.parent.name,
            JinjaTemplateVars.config_file_name.name: path.name,
        }
        rendered = render_template(f.read(), template_kw, **kwargs, **kw)
    return rendered


def render_template(source: str, template_kw: Optional[dict] = None, **kwargs):
    """
    Render a template from a path.

    Parameters
    ----------
    path : str
        Path to the template file.
    template_kw : dict, optional
        Dictionary of keyword arguments to pass to the jinja2.Template constructor.
    **kwargs
        Keyword arguments to pass to the template as variables to render.
    """
    template_kw = template_kw if template_kw is not None else {}
    template_kw.setdefault("extensions", []).append("jinja2.ext.do")
    kwargs["load_py"] = importlib.import_module
    template = jinja2.Template(source, **template_kw)
    return template.render(
        **kwargs,
    )
