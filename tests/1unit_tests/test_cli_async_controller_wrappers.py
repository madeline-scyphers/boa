import json
import sys

import pandas as pd
import pytest
from click.testing import CliRunner

import boa.async_opt as async_opt
import boa.plot as plot_mod
from boa import BOAConfig, Controller, ScriptWrapper, cd_and_cd_back
from boa.ax_api import TrialStatus, FailureRateExceededError
from boa.client import get_client
from boa.scripts import synth_func_cli
from boa.wrappers.base_wrapper import BaseWrapper
from boa.wrappers.synthetic_wrapper import SyntheticWrapper
from boa.wrappers.wrapper_utils import get_trial_dir

from behavior_helpers import DeterministicWrapper, deterministic_client, deterministic_wrapper, passthrough_config


class ExtraMetricWrapper(DeterministicWrapper):
    def fetch_trial_data(self, trial, metric_name=None, **kwargs):
        return {"metric": 1.0, "extra": 2.0}


def write_script(path, content):
    path.write_text(content)
    return path


def script_config(experiment_dir, command, n_trials=1):
    return BOAConfig(
        optimization={"objective": "metric", "metrics": {"metric": {"metric_type": "passthrough"}}},
        generation_strategy={"method": "fast", "initialization_budget": 1},
        orchestrator={"total_trials": n_trials, "max_pending_trials": 1},
        parameters={"x": {"type": "range", "bounds": [0.0, 1.0], "parameter_type": "float"}},
        n_trials=n_trials,
        script_options={
            "experiment_dir": str(experiment_dir),
            "append_timestamp": False,
            "run_model": command,
        },
    )


def test_synth_func_cli_writes_language_agnostic_output(tmp_path):
    result = CliRunner().invoke(
        synth_func_cli.main,
        ["--output_dir", str(tmp_path), "--input_size", "3", "--standard_dev", "0", "1", "2"],
    )

    assert result.exit_code == 0
    output = json.loads((tmp_path / "output.json").read_text())
    assert output["metric_name"] == "branin"
    assert output["input"] == [[1.0, 2.0], [1.0, 2.0], [1.0, 2.0]]
    assert len(output["output"]) == 3


def test_plot_app_builder_returns_panel_app(branin_main_run):
    apps = plot_mod.build_plot_apps(branin_main_run)

    assert list(apps) == [plot_mod.__file__.split("/")[-1]]


def test_async_helpers_attach_completed_csv_rows_and_generate_pending_trials(tmp_path):
    client = deterministic_client(experiment_dir=tmp_path, n_trials=2)[0]

    async_opt.generate_pending_trials(client=client, n_trials=2)
    assert len(client.experiment.trials) == 2
    assert all(trial.status == TrialStatus.RUNNING for trial in client.experiment.trials.values())

    pd.DataFrame(
        [
            {"trial_index": 0, "metric": 1.5},
            {"trial_index": 1, "metric": None},
            {"trial_index": 99, "metric": 9.9},
        ]
    ).to_csv(client.optimization_csv, index=False)

    async_opt.exp_attach_data_from_opt_csv(["metric"], client)

    assert client.experiment.trials[0].status == TrialStatus.COMPLETED
    assert client.experiment.trials[1].status == TrialStatus.RUNNING


def test_async_run_uses_real_config_and_loaded_client(tmp_path):
    config_path = tmp_path / "async.yaml"
    experiment_dir = tmp_path / "async_exp"
    config_path.write_text(
        "\n".join(
            [
                "optimization:",
                "  objective: metric",
                "  metrics:",
                "    metric:",
                "      metric_type: passthrough",
                "generation_strategy:",
                "  method: fast",
                "  initialization_budget: 2",
                "n_trials: 1",
                "parameters:",
                "  x:",
                "    type: range",
                "    bounds: [0.0, 1.0]",
                "    parameter_type: float",
                "script_options:",
                f"  experiment_dir: {experiment_dir}",
                "  append_timestamp: false",
            ]
        )
    )

    client = async_opt.run(config_path=config_path, client_path="", num_trials=1)
    loaded = async_opt.run(config_path=None, client_path=client.client_filepath, num_trials=1)

    assert client.optimization_csv.exists()
    assert loaded.client_filepath == client.client_filepath
    assert len(loaded.experiment.trials) >= 1


def test_async_config_options_resolve_working_dir(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    with cd_and_cd_back(tmp_path):
        opts = async_opt.get_config_options({"working_dir": "work", "append_timestamp": False})

    assert opts["working_dir"] == work
    assert opts["append_timestamp"] is False
    assert async_opt._prepend_rel_path(tmp_path, None) is None


def test_controller_initialization_run_and_from_client(tmp_path):
    wrapper = deterministic_wrapper(experiment_dir=tmp_path, n_trials=1)
    controller = Controller(wrapper=wrapper)
    client, initialized_wrapper = controller.initialize_client()

    assert initialized_wrapper is wrapper
    assert controller.run() is client
    assert client.client_filepath.exists()
    assert client.optimization_csv.exists()

    loaded_controller = Controller.from_client(client)
    assert loaded_controller.client is client
    assert loaded_controller.wrapper is wrapper


def test_script_wrapper_runs_real_subprocess_and_reads_output(tmp_path):
    script_path = write_script(
        tmp_path / "write_output.py",
        "import json, pathlib, sys\n"
        "trial_dir = pathlib.Path(sys.argv[-1])\n"
        "(trial_dir / 'output.json').write_text(json.dumps({'metric': 3.0}))\n",
    )
    command = f"{sys.executable} {script_path}"
    config = script_config(experiment_dir=tmp_path / "script_exp", command=command)
    wrapper = ScriptWrapper(config=config)
    client = get_client(config=config, wrapper=wrapper)

    client.run_trials(max_trials=1)

    trial = client.experiment.trials[0]
    output = json.loads((get_trial_dir(wrapper.experiment_dir, trial.index) / "output.json").read_text())
    assert trial.status == TrialStatus.COMPLETED
    assert output == {"metric": 3.0}


def test_script_wrapper_failed_status_from_real_subprocess(tmp_path):
    script_path = write_script(
        tmp_path / "write_failed.py",
        "import json, pathlib, sys\n"
        "trial_dir = pathlib.Path(sys.argv[-1])\n"
        "(trial_dir / 'trial_status.json').write_text(json.dumps({'trial_status': 'FAILED'}))\n",
    )
    config = script_config(experiment_dir=tmp_path / "failed_exp", command=f"{sys.executable} {script_path}")
    wrapper = ScriptWrapper(config=config)
    client = get_client(config=config, wrapper=wrapper)

    with pytest.raises(FailureRateExceededError):
        client.run_trials(max_trials=1)


def test_synthetic_wrapper_returns_metric_values_and_marks_complete(tmp_path):
    config = passthrough_config(experiment_dir=tmp_path, n_trials=1)
    wrapper = SyntheticWrapper(config=config, metrics={"metric": [7.0]})
    client = get_client(config=config, wrapper=wrapper)

    client.run_trials(max_trials=1)

    assert client.experiment.trials[0].status == TrialStatus.COMPLETED
    assert client.summarize()["metric"].iloc[0] == 7.0


def test_base_wrapper_config_loading_paths_properties_and_from_dict(tmp_path):
    raw = passthrough_config(experiment_dir=tmp_path / "raw", n_trials=1).to_dict()
    raw["optimization"]["metrics"]["metric"]["properties"] = {"kind": "demo"}
    wrapper = DeterministicWrapper(config=raw, experiment_dir=tmp_path / "raw", append_timestamp=False)

    assert wrapper.metric_params == {"metric": []}
    assert wrapper._metric_properties == {"metric": {"kind": "demo"}}
    wrapper.working_dir = "work"
    wrapper.output_dir = "out"
    assert wrapper.working_dir.is_absolute()
    assert wrapper.output_dir.is_absolute()

    restored_dir = tmp_path / "restored"
    restored_dir.mkdir()
    restored = DeterministicWrapper.from_dict(config=raw, experiment_dir=restored_dir, metric_names=["metric"])
    assert restored.config_path.name == "temp_config.yaml"
    assert restored.metric_names == ["metric"]
    assert restored.to_dict()["name"] == "DeterministicWrapper"


def test_base_wrapper_fetch_trial_data_cache_and_error_paths(tmp_path):
    wrapper = deterministic_wrapper(experiment_dir=tmp_path, n_trials=1)
    client = get_client(config=wrapper.config, wrapper=wrapper)
    trial_index = next(iter(client.get_next_trials(max_trials=1)))
    trial = client.experiment.trials[trial_index]
    wrapper.run_model(trial)

    with pytest.raises(TypeError, match="trial_index"):
        wrapper._fetch_trial_data(parameters={"x": 1.0}, metric_name="metric")

    first = wrapper._fetch_trial_data(parameters=trial.arm.parameters, metric_name="metric", trial=trial)
    wrapper.values[trial.index] = 100.0
    second = wrapper._fetch_trial_data(parameters=trial.arm.parameters, metric_name="metric", trial=trial)

    assert first == second

    extra_wrapper = ExtraMetricWrapper(config=wrapper.config, experiment_dir=tmp_path / "extra", append_timestamp=False)
    extra_wrapper.metric_names = ["metric"]
    extra_trial_index = next(iter(get_client(config=extra_wrapper.config, wrapper=extra_wrapper).get_next_trials(1)))
    extra_trial = client.experiment.trials[trial_index]
    with pytest.raises(ValueError, match="extra returned metric"):
        extra_wrapper._fetch_trial_data(parameters=extra_trial.arm.parameters, metric_name="metric", trial_index=extra_trial_index)


def test_base_wrapper_from_dict_resolves_moved_config_and_allows_no_config(tmp_path):
    raw = passthrough_config(experiment_dir=tmp_path / "exp", n_trials=1).to_dict()
    exp_dir = tmp_path / "exp"
    exp_dir.mkdir()
    config_path = exp_dir / "old_config.yaml"

    from boa.utils import yaml_dump

    yaml_dump(raw, config_path)
    restored = DeterministicWrapper.from_dict(config_path=tmp_path / "missing" / "old_config.yaml", experiment_dir=exp_dir)
    assert restored.config_path == config_path

    no_config = DeterministicWrapper.from_dict(experiment_dir=tmp_path / "no_config")
    assert no_config.config is None
