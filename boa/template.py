from __future__ import annotations

import importlib
import pathlib
from enum import Enum
from typing import Optional

import jinja2


class JinjaTemplateVars(Enum):
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
    if template_kw is None:
        template_kw = {}
    template_kw.setdefault("extensions", []).append("jinja2.ext.do")
    kwargs["load_py"] = importlib.import_module
    with open(path) as f:
        template = jinja2.Template(f.read(), **template_kw)
    kw = {
        JinjaTemplateVars.config_path.name: path,
        JinjaTemplateVars.config_dir_name.name: path.parent.name,
        JinjaTemplateVars.config_file_name.name: path.name,
    }
    return template.render(
        **kwargs,
        **kw,
    )
