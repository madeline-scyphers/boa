from boa import BOAConfig, load_json_from_str, load_jsonlike, load_yaml_from_str
from boa.definitions import ROOT, PathLike

TEST_CONFIG_DIR = ROOT / "tests" / "test_configs"


def test_config_with_jinja2():
    config = BOAConfig.from_jsonlike(TEST_CONFIG_DIR / "test_config_jinja2.yaml")
    assert len(config.parameters) == 13
    assert len(config.parameter_constraints) == 13


def test_load_jsonlike_handles_jinja_ext(tmp_path):
    yaml_path = tmp_path / "config.yaml.j2"
    json_path = tmp_path / "config.json.j2"
    with open(yaml_path, "w") as f:
        f.write("{% set x = 1 %}\n")
        f.write("x: {{ x }}\n")
    with open(json_path, "w") as f:
        f.write("{% set x = 1 %}\n")
        f.write('{"x": {{ x }}}\n')
    config_y = load_jsonlike(yaml_path)
    config_j = load_jsonlike(json_path)
    assert config_y["x"] == 1
    assert config_j["x"] == 1


def test_template_with_commented_out_vars_in_style_of_config_format():
    yaml_config = """
    {% set x = 1 %}
    {# {% set x = 2 %} #}
    x: {{ x }}
    """
    config = load_yaml_from_str(yaml_config)
    assert config["x"] == 1

    json_config = """
    {% set x = 1 %}
    {# {% set x = 2 %} #}
    {"x": {{ x }}}
    """
    config = load_json_from_str(json_config)
    assert config["x"] == 1
