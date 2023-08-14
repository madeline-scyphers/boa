import numpy as np
import pytest
from ax import MultiObjectiveOptimizationConfig, OptimizationConfig

from boa import (
    BaseWrapper,
    Controller,
    get_metric_by_class_name,
    get_metric_from_config,
    setup_synthetic_metric,
)


class Wrapper(BaseWrapper):
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


class WrapperPassThrough(Wrapper):
    def fetch_trial_data(self, trial, metric_properties, metric_name, *args, **kwargs):
        return trial.index


def test_load_metric_by_name():
    metric_synth = setup_synthetic_metric("Hartmann4")
    assert metric_synth.name == "Hartmann4"
    assert metric_synth.metric_to_eval.name == "FromBotorch_Hartmann4"

    metric_synth = setup_synthetic_metric("Hartmann4", name="something")
    assert metric_synth.name == "something"
    assert metric_synth.metric_to_eval.name == "FromBotorch_Hartmann4"

    metric_sklearn = get_metric_by_class_name("MSE")
    assert metric_sklearn.name == "MSE"
    assert metric_sklearn.metric_to_eval.__name__ == "mean_squared_error"

    metric_sklearn = get_metric_by_class_name("MSE", name="something")
    assert metric_sklearn.name == "something"
    assert metric_sklearn.metric_to_eval.__name__ == "mean_squared_error"


def test_load_metric_from_config(synth_config, metric_config):
    metrics = synth_config.objective.metrics
    for metric_c in metrics:
        metric = get_metric_from_config(metric_c)
        assert metric.name == "Hartmann4"
        assert metric.metric_to_eval.name == "FromBotorch_Hartmann4"

    metrics = metric_config.objective.metrics
    for metric_c in metrics:
        if not metric_c.info_only:
            metric = get_metric_from_config(metric_c)
            assert metric.name == "rmse"
            assert metric.metric_to_eval.__name__ == "mean_squared_error"


def test_metric_fetch_trial_data_works_with_wrapper_fetch_trial_data_and_test_sem_passing(moo_config, tmp_path):
    controller = Controller(config=moo_config, wrapper=Wrapper, experiment_dir=tmp_path)
    controller.initialize_scheduler()

    scheduler = controller.scheduler
    experiment = controller.experiment
    wrapper = controller.wrapper

    prev_f_ret = None
    for _ in range(5):
        trial = experiment.new_trial(generator_run=scheduler.generation_strategy.gen(experiment))
        for name, metric in experiment.metrics.items():
            ok = metric.fetch_trial_data(trial)
            data = ok.value
            sem = wrapper._metric_cache[trial.index][name].pop("sem", None)
            f_ret = metric.f(**controller.wrapper._metric_cache[trial.index][name])
            assert f_ret == data.df["mean"].iloc[0]

            if sem:
                assert data.df["sem"].iloc[0] == sem

            assert f_ret != prev_f_ret
            prev_f_ret = f_ret


def test_metric_fetch_trial_data_works_with_wrapper_fetch_trial_all_data_and_test_sem_fails_with_wrong_metrics(
    moo_config, caplog, tmp_path
):
    orig_metrics = moo_config.objective.metrics
    moo_config.objective.metrics = orig_metrics[:1]
    controller = Controller(config=moo_config, wrapper=Wrapper, experiment_dir=tmp_path)
    controller.initialize_scheduler()

    scheduler = controller.scheduler
    experiment = controller.experiment

    trial = experiment.new_trial(generator_run=scheduler.generation_strategy.gen(experiment))
    with pytest.raises(ValueError):
        for name, metric in experiment.metrics.items():
            metric.fetch_trial_data(trial)


def test_metric_fetch_trial_data_works_with_wrapper_fetch_trial_data_single_and_test_sem_passing(moo_config, tmp_path):
    controller = Controller(config=moo_config, wrapper=Wrapper, fetch_all=False, experiment_dir=tmp_path)
    controller.initialize_scheduler()

    scheduler = controller.scheduler
    experiment = controller.experiment
    wrapper = controller.wrapper

    prev_f_ret = None
    for _ in range(5):
        trial = experiment.new_trial(generator_run=scheduler.generation_strategy.gen(experiment))
        for name, metric in experiment.metrics.items():
            ok = metric.fetch_trial_data(trial)
            data = ok.value
            kw = wrapper.fetch_trial_data(trial, {}, name)
            sem = kw.pop("sem", None)
            f_ret = metric.f(**kw)
            assert f_ret == data.df["mean"].iloc[0]

            if sem:
                assert data.df["sem"].iloc[0] == sem

            assert f_ret != prev_f_ret
            prev_f_ret = f_ret


def test_can_create_info_only_metrics(metric_config, tmp_path):
    controller = Controller(config=metric_config, wrapper=Wrapper, experiment_dir=tmp_path)
    controller.initialize_scheduler()

    assert isinstance(controller.scheduler.experiment.optimization_config, OptimizationConfig)
    assert not isinstance(controller.scheduler.experiment.optimization_config, MultiObjectiveOptimizationConfig)

    assert len(controller.scheduler.experiment.tracking_metrics) > 0


def test_pass_through_metric_passes_through_value(pass_through_config, tmp_path):
    controller = Controller(
        config=pass_through_config, wrapper=WrapperPassThrough, fetch_all=False, experiment_dir=tmp_path
    )
    controller.initialize_scheduler()

    scheduler = controller.scheduler
    experiment = controller.experiment
    wrapper = controller.wrapper

    for _ in range(5):
        trial = experiment.new_trial(generator_run=scheduler.generation_strategy.gen(experiment))
        for name, metric in experiment.metrics.items():
            ok = metric.fetch_trial_data(trial)
            data = ok.value
            f_ret = metric.f(wrapper.fetch_trial_data(trial, {}, name))
            assert f_ret == data.df["mean"].iloc[0]
            assert f_ret == trial.index
