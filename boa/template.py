from __future__ import annotations

from typing import Optional

import jinja2


def render_template_from_path(path, template_kw: Optional[dict] = None, **kwargs):
    if template_kw is None:
        template_kw = {}
    template_kw["extensions"].append("jinja2.ext.do")
    with open(path) as f:
        template = jinja2.Template(f.read(), **template_kw)
    return template.render(**kwargs)
