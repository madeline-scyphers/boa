import jinja2


def render_template(template_name, **kwargs):
    template = jinja2.Environment(loader=jinja2.FileSystemLoader("templates")).get_template(template_name)
    return template.render(**kwargs)
