import json
import subprocess
import sys
from functools import partial

import numpy as np
import panel as pn
import pytest

import boa.plotting as plotting
from boa import BOAMetric
from boa.ax_api import AxError
from boa.metrics.metrics import (
    BOASklearnMetric,
    PassThrough,
    _get_boa_metric_any_case,
    get_boa_metric,
    get_metric_by_class_name,
    get_metric_from_config,
)
from boa.metrics.modular_metric import ModularMetric, _get_func_by_name, _get_name
from boa.storage import client_from_json_file, client_to_json_file
from boa.wrappers.wrapper_utils import initialize_wrapper, make_trial_dir, save_trial_data

from behavior_helpers import deterministic_client


def add_with_offset(a, b=0):
    return a + b


def identity(x):
    return x


class InvalidMetricConfig:
    metric = "metric"
    metric_type = "unknown"

    def to_dict(self):
        return {"metric": "metric", "name": "metric", "metric_type": "unknown"}


def test_module_main_delegates_to_real_cli_entrypoint():
    result = subprocess.run([sys.executable, "-m", "boa", "--help"], capture_output=True, text=True, timeout=20)

    assert result.returncode == 0
    assert "Usage" in result.stdout


def test_modular_metric_name_resolution_invalid_results_clone_and_fetch_cache():
    assert _get_func_by_name("mean") is np.mean
    with pytest.raises(ValueError):
        _get_func_by_name("not_a_metric")
    assert _get_name(partial(np.mean)) == "mean"

    metric = ModularMetric(metric_to_eval=add_with_offset, name="sum", metric_func_kwargs={"b": 2}, noise_sd=None)
    assert metric._evaluate({"kwargs": {"wrapper_args": 3}}) == 5
    assert metric.fetch(trial_index=0, trial_metadata={"sum": {"wrapper_args": 4}, "progression": 7}) == (7, 6.0)
    assert metric.fetch(trial_index=0, trial_metadata={"sum": {"wrapper_args": 100}}) == (7, 6.0)
    assert metric.clone().name == "sum"
    assert metric.to_dict()["metric_to_eval"] == "add_with_offset"

    for invalid in [None, "nan", {"x": np.nan}, [1, np.nan]]:
        assert ModularMetric._has_invalid_result(invalid)
    assert not ModularMetric._has_invalid_result({"x": 1})

    with pytest.raises(ValueError, match="NaNs"):
        ModularMetric(metric_to_eval=identity).fetch(trial_index=1, trial_metadata={"identity": {"wrapper_args": np.nan}})

    with pytest.raises(TypeError):
        ModularMetric()


def test_metric_registry_and_passthrough_edges():
    pass_through = PassThrough()
    assert pass_through._evaluate({"kwargs": {"wrapper_args": 5}}) == 5
    with pytest.raises(ValueError, match="one value"):
        pass_through._evaluate({"kwargs": {"wrapper_args": [1, 2]}})

    assert get_metric_by_class_name("Mean", instantiate=False).__name__ == "Mean"
    assert isinstance(_get_boa_metric_any_case("mean"), type)
    with pytest.raises(ValueError):
        get_boa_metric("missing_metric")
    with pytest.raises(KeyError):
        get_metric_from_config(InvalidMetricConfig())

    sklearn_metric = BOASklearnMetric(metric_to_eval="median_absolute_error")
    assert sklearn_metric._to_eval_name == "median_absolute_error"
    configured = get_metric_from_config(BOAMetric(metric="median_absolute_error", metric_type="sklearn"))
    assert configured.name == "median_absolute_error"


def test_plotting_helpers_with_real_completed_clients(branin_main_run, moo_main_run):
    trace = plotting.plot_metrics_trace(branin_main_run)
    contours = plotting.plot_contours(branin_main_run)
    slice_plot = plotting.plot_slice(branin_main_run)
    pareto = plotting.plot_pareto_frontier(moo_main_run)
    app = plotting.app_view(branin_main_run)

    assert isinstance(trace, pn.reactive.Reactive)
    assert isinstance(contours, pn.reactive.Reactive)
    assert isinstance(slice_plot, pn.reactive.Reactive)
    assert isinstance(pareto, pn.reactive.Reactive)
    assert hasattr(app, "main")
    assert len(app.main) > 0
    assert not plotting.scheduler_to_df(branin_main_run).empty


def test_storage_load_reattaches_real_wrapper(tmp_path):
    client, wrapper = deterministic_client(experiment_dir=tmp_path, n_trials=1)
    client.run_trials(max_trials=1)
    client_to_json_file(client, client_filepath="client.json", dir_=tmp_path)

    loaded = client_from_json_file(tmp_path / "client.json", wrapper=wrapper)

    assert loaded.wrapper is wrapper
    assert loaded.experiment.runner.wrapper is wrapper


def test_initialize_wrapper_path_errors_and_save_trial_data(tmp_path):
    missing_path = tmp_path / "missing.py"
    with pytest.raises(AxError, match="Could not load wrapper"):
        initialize_wrapper(missing_path)

    client = deterministic_client(experiment_dir=tmp_path / "exp", n_trials=1)[0]
    trial_index = next(iter(client.get_next_trials(max_trials=1)))
    trial = client.experiment.trials[trial_index]
    trial_dir = make_trial_dir(tmp_path, trial.index)

    saved_dir = save_trial_data(
        trial,
        trial_dir=trial_dir,
        param_names={"metric": ["x"]},
        unserializable=object(),
    )

    assert saved_dir == trial_dir
    assert json.loads((trial_dir / "filtered_parameters.json").read_text()) == {"metric": {"x": trial.arm.parameters["x"]}}
    assert "unserializable" in json.loads((trial_dir / "data.json").read_text())

    with pytest.raises(AxError, match="Parameter metric"):
        save_trial_data(trial, trial_dir=tmp_path / "bad", param_names={"metric": ["missing"]})
