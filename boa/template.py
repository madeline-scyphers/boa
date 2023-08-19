from __future__ import annotations

from typing import Optional

import jinja2


def render_template_from_path(path, template_kw: Optional[dict] = None, **kwargs):
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
    if template_kw is None:
        template_kw = {}
    template_kw.setdefault("extensions", []).append("jinja2.ext.do")
    with open(path) as f:
        template = jinja2.Template(f.read(), **template_kw)
    return template.render(**kwargs)
