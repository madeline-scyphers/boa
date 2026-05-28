import json

import pytest

from boa import load_jsonlike
from boa.storage import _path_from_json_value, client_to_csv, client_to_json_file, dump_client_data
from boa.utils import (
    _load_attr_from_module,
    _load_module_from_path,
    check_min_package_version,
    convert_type,
    get_dictionary_matching_signature,
    serialize_init_args,
    yaml_dump,
)

from behavior_helpers import InitArgObject, deterministic_client, parse_int_string


def test_client_options_paths_and_csv_serialization(tmp_path):
    client, wrapper = deterministic_client(experiment_dir=tmp_path, n_trials=1)

    assert client.client_filepath == wrapper.experiment_dir / "client.json"
    assert client.optimization_csv == wrapper.experiment_dir / "optimization.csv"
    assert client._resolve_orchestrator_options(parallelism=3).max_pending_trials == 3
    assert client._resolve_orchestrator_options(
        tolerated_trial_failure_rate=0.2,
        initial_seconds_between_polls=5,
    ).tolerated_trial_failure_rate == 0.2
    client.run_trials()
    assert len(client.experiment.trials) == 1

    csv_path = client_to_csv(client, opt_filepath="summary.csv", dir_=tmp_path, metrics_to_end=True)
    assert csv_path == tmp_path / "summary.csv"
    assert csv_path.exists()
    assert "trial_index" in csv_path.read_text()


def test_client_json_helpers_write_expected_paths(tmp_path):
    client = deterministic_client(experiment_dir=tmp_path, n_trials=1)[0]
    client.run_trials(max_trials=1)
    json_path = tmp_path / "state.json"
    csv_path = tmp_path / "summary.csv"

    client_to_json_file(client, client_filepath="state.json", dir_=tmp_path)
    dump_client_data(client, client_filepath=json_path, opt_filepath=csv_path)

    assert json.loads(json_path.read_text())["boa_version"]
    assert csv_path.exists()
    assert client.client_filepath == json_path
    assert client.optimization_csv == csv_path
    assert _path_from_json_value({"pathsegments": [str(tmp_path), "state.json"]}) == json_path


def test_general_utils_cover_signature_loading_conversion_and_yaml(tmp_path):
    def func(public, private=None, **kwargs):
        return public, private, kwargs

    matched = get_dictionary_matching_signature(
        __import__("inspect").signature(func),
        {"public": 1, "_private": 2, "extra": 3},
        match_private=True,
        exclude_fields=["extra"],
        accept_all_kwargs=False,
    )

    assert matched == {"public": 1, "private": 2}
    assert convert_type({"1": ["2", "x"]}, {str: parse_int_string}) == {1: [2, "x"]}
    assert check_min_package_version("pip", "0")

    module_path = tmp_path / "module.py"
    module_path.write_text("VALUE = 42\n")
    module = _load_module_from_path(module_path)
    assert _load_attr_from_module(module, "VALUE") == 42
    with pytest.raises(AttributeError):
        _load_attr_from_module(module, "MISSING")

    yaml_path = tmp_path / "data.yaml"
    yaml_dump({"a": 1}, yaml_path)
    assert load_jsonlike(yaml_path) == {"a": 1}
    with pytest.raises(ValueError):
        load_jsonlike(tmp_path / "data.txt")
    assert serialize_init_args(InitArgObject(), match_private=True)["private"] == 2
