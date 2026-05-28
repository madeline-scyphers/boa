import numpy as np
import pytest

from boa import (
    BaseWrapper,
    BOAMetric,
    get_metric_by_class_name,
    get_metric_from_config,
    setup_sklearn_metric,
    setup_synthetic_metric,
)
from boa.ax_api import MultiObjectiveOptimizationConfig, OptimizationConfig
from boa.client import get_client


class WrapperForTestss(BaseWrapper):
    def __init__(self, *args, fetch_all=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fetch_all = fetch_all

    def run_model(self, trial) -> None:
        pass

    def set_trial_status(self, trial) -> None:
        trial.mark_completed()

    def fetch_trial_data(self, trial, metric_properties, metric_name, *args, **kwargs):
        if self.fetch_all:
            idx = trial.index + 1
            return {
                "Meanyyy": {"a": idx * np.array([-0.3691, 4.6544, 1.2675, -0.4327]), "sem": 4.5},
                "RMSE": {
                    "y_true": idx * np.array([1.12, 1.25, 2.54, 4.52]),
                    "y_pred": idx * np.array([1.51, 1.01, 2.21, 4.50]),
                },
            }
        else:
            idx = trial.index + 1
            if metric_name == "Meanyyy":
                return {"a": idx * np.array([-0.3691, 4.6544, 1.2675, -0.4327]), "sem": 4.5}
            elif metric_name == "RMSE":
                return {
                    "y_true": idx * np.array([1.12, 1.25, 2.54, 4.52]),
                    "y_pred": idx * np.array([1.51, 1.01, 2.21, 4.50]),
                }


class WrapperPassThrough(WrapperForTestss):
    def fetch_trial_data(self, trial, metric_properties, metric_name, *args, **kwargs):
        return trial.index


def _configured_wrapper(config, wrapper_cls, tmp_path, **kwargs):
    metric_names = list(config.optimization.metrics) + list(config.optimization.tracking_metrics)
    return wrapper_cls(config=config, experiment_dir=tmp_path, metric_names=metric_names, **kwargs)


def _metric_map(config, wrapper):
    return {
        name: get_metric_from_config(config=metric_config, wrapper=wrapper)
        for name, metric_config in config.optimization.metrics.items()
    }


def _mean_sem(outcome):
    if isinstance(outcome, tuple):
        return outcome
    return outcome, None


def test_load_metric_by_name():
    metric_synth = setup_synthetic_metric("Hartmann4")
    assert metric_synth.name == "Hartmann4"
    assert metric_synth.metric_to_eval.name == "FromBotorch_Hartmann4"

    metric_synth = setup_synthetic_metric("Hartmann4", name="something")
    assert metric_synth.name == "something"
    assert metric_synth.metric_to_eval.name == "FromBotorch_Hartmann4"

    metric_boa = get_metric_by_class_name("MSE")
    assert metric_boa.name == "MSE"
    assert metric_boa.metric_to_eval.__name__ == "mean_squared_error"

    metric_boa = get_metric_by_class_name("MSE", name="something")
    assert metric_boa.name == "something"
    assert metric_boa.metric_to_eval.__name__ == "mean_squared_error"

    metric_sklearn = setup_sklearn_metric("median_absolute_error")
    assert metric_sklearn.name == "median_absolute_error"
    assert metric_sklearn.metric_to_eval.__name__ == "median_absolute_error"

    metric_sklearn = setup_sklearn_metric("median_absolute_error", name="something")
    assert metric_sklearn.name == "something"
    assert metric_sklearn.metric_to_eval.__name__ == "median_absolute_error"


def test_load_metric_from_config(synth_config, generic_config):
    metrics = synth_config.optimization.metrics.values()
    for metric_c in metrics:
        metric = get_metric_from_config(metric_c)
        assert metric.name == "Hartmann4"
        assert metric.metric_to_eval.name == "FromBotorch_Hartmann4"

    metrics = generic_config.optimization.metrics.values()
    for metric_c in metrics:
        if metric_c.name not in generic_config.optimization.tracking_metrics:
            metric = get_metric_from_config(metric_c)
            assert metric.name == "rmse"
            assert metric.metric_to_eval.__name__ == "root_mean_squared_error"


def test_metric_fetch_trial_data_works_with_wrapper_fetch_trial_data_and_test_sem_passing(moo_config, tmp_path):
    wrapper = _configured_wrapper(moo_config, WrapperForTestss, tmp_path)
    metrics = _metric_map(moo_config, wrapper)

    prev_f_ret = None
    for trial_index in range(5):
        for name, metric in metrics.items():
            _, outcome = metric.fetch(trial_index=trial_index, trial_metadata={})
            mean, sem_from_fetch = _mean_sem(outcome)
            sem = wrapper._metric_cache[trial_index][name].pop("sem", None)
            f_ret = metric.f(**wrapper._metric_cache[trial_index][name])
            assert f_ret == mean

            if sem:
                assert sem_from_fetch == sem

            assert f_ret != prev_f_ret
            prev_f_ret = f_ret


def test_metric_fetch_trial_data_works_with_wrapper_fetch_trial_all_data_and_test_sem_fails_with_wrong_metrics(
    moo_config, caplog, tmp_path
):
    moo_config.optimization.objective = "RMSE"
    moo_config.optimization.metrics.pop("Meanyyy")
    wrapper = _configured_wrapper(moo_config, WrapperForTestss, tmp_path)
    metrics = _metric_map(moo_config, wrapper)
    with pytest.raises(ValueError):
        for metric in metrics.values():
            metric.fetch(trial_index=0, trial_metadata={})


def test_metric_fetch_trial_data_works_with_wrapper_fetch_trial_data_single_and_test_sem_passing(moo_config, tmp_path):
    wrapper = _configured_wrapper(moo_config, WrapperForTestss, tmp_path, fetch_all=False)
    metrics = _metric_map(moo_config, wrapper)

    prev_f_ret = None
    for trial_index in range(5):
        for name, metric in metrics.items():
            _, outcome = metric.fetch(trial_index=trial_index, trial_metadata={})
            mean, sem_from_fetch = _mean_sem(outcome)
            trial = type("TrialContext", (), {"index": trial_index})()
            kw = wrapper.fetch_trial_data(trial, {}, name)
            sem = kw.pop("sem", None)
            f_ret = metric.f(**kw)
            assert f_ret == mean

            if sem:
                assert sem_from_fetch == sem

            assert f_ret != prev_f_ret
            prev_f_ret = f_ret


def test_can_create_info_only_metrics(generic_config, tmp_path):
    wrapper = _configured_wrapper(generic_config, WrapperForTestss, tmp_path)
    client = get_client(config=generic_config, wrapper=wrapper, runner=object())

    assert isinstance(client.experiment.optimization_config, OptimizationConfig)
    assert not isinstance(client.experiment.optimization_config, MultiObjectiveOptimizationConfig)

    assert len(client.experiment.tracking_metrics) > 0


def test_pass_through_metric_passes_through_value(pass_through_config, tmp_path):
    wrapper = _configured_wrapper(pass_through_config, WrapperPassThrough, tmp_path, fetch_all=False)
    metrics = _metric_map(pass_through_config, wrapper)

    for trial_index in range(5):
        for name, metric in metrics.items():
            _, outcome = metric.fetch(trial_index=trial_index, trial_metadata={})
            mean, sem = _mean_sem(outcome)
            trial = type("TrialContext", (), {"index": trial_index})()
            f_ret = metric.f(wrapper.fetch_trial_data(trial, {}, name))
            assert f_ret == mean
            assert f_ret == trial_index
            assert sem == metric.noise_sd


def test_can_override_metric_func_kwargs():
    x = [1, 2, 3, 4, 5, 6]
    y = [0.1 * i for i in reversed(x)]
    returns = []
    normalizers = ["iqr", "std", "mean", "range"]
    for normalizer in normalizers:
        config = BOAMetric(**dict(metric="NRMSE", metric_func_kwargs=dict(normalizer=normalizer)))
        metric = get_metric_from_config(config)
        assert metric.metric_to_eval.__name__ == "normalized_root_mean_squared_error"
        returns.append(metric.f(x, y))
    # All the normalized values should be different, ensuring that the kwargs are passed through
    assert len(set(returns)) == len(normalizers)
