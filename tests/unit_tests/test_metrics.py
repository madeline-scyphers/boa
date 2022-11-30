import tempfile

import numpy as np
import pytest

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

    def set_trial_status(self, trial) -> None:
        trial.mark_completed()

    def fetch_all_trial_data(self, trial, metric_properties, *args, **kwargs):
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
            return

    def fetch_trial_data_single(self, trial, metric_properties, metric_name, *args, **kwargs):
        if not self.fetch_all:
            idx = trial.index + 1
            if metric_name == "Meanyyy":
                return {"a": idx * np.array([-0.3691, 4.6544, 1.2675, -0.4327]), "sem": 4.5}
            elif metric_name == "RMSE":
                return {
                    "y_true": idx * np.array([1.12, 1.25, 2.54, 4.52]),
                    "y_pred": idx * np.array([1.51, 1.01, 2.21, 4.50]),
                }
        else:
            return


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
    objectives = synth_config["optimization_options"]["objective_options"]["objectives"]
    for objective in objectives:
        metric = get_metric_from_config(objective)
        assert metric.name == "Hartmann4"
        assert metric.metric_to_eval.name == "FromBotorch_Hartmann4"

    objectives = metric_config["optimization_options"]["objective_options"]["objectives"]
    for objective in objectives:
        metric = get_metric_from_config(objective)
        assert metric.name == "rmse"
        assert metric.metric_to_eval.__name__ == "mean_squared_error"


def test_metric_fetch_trial_data_works_with_wrapper_fetch_all_trial_data_and_test_sem_passing(moo_config, tmp_path):
    controller = Controller(config=moo_config, wrapper=Wrapper)
    controller.setup(experiment_dir=tmp_path)

    scheduler = controller.scheduler
    experiment = controller.experiment
    wrapper = controller.wrapper

    prev_f_ret = None
    for _ in range(5):
        trial = experiment.new_trial(generator_run=scheduler.generation_strategy.gen(experiment))
        for name, metric in experiment.metrics.items():
            ok = metric.fetch_trial_data(trial)
            data = ok.value
            sem = wrapper._metric_dict[trial.index][name].pop("sem", None)
            f_ret = metric.f(**controller.wrapper._metric_dict[trial.index][name])
            assert f_ret == data.df["mean"].iloc[0]

            if sem:
                assert data.df["sem"].iloc[0] == sem

            assert f_ret != prev_f_ret
            prev_f_ret = f_ret


def test_metric_fetch_trial_data_works_with_wrapper_fetch_all_trial_data_and_test_sem_fails_with_wrong_metrics(
    moo_config, caplog, tmp_path
):
    orig_metrics = moo_config["optimization_options"]["objective_options"]["objectives"]
    moo_config["optimization_options"]["objective_options"]["objectives"] = orig_metrics[:1]
    controller = Controller(config=moo_config, wrapper=Wrapper)
    controller.setup(experiment_dir=tmp_path)

    scheduler = controller.scheduler
    experiment = controller.experiment

    trial = experiment.new_trial(generator_run=scheduler.generation_strategy.gen(experiment))
    for name, metric in experiment.metrics.items():
        metric.fetch_trial_data(trial)

    assert "found extra returned metric: " in caplog.text

    moo_config["optimization_options"]["objective_options"]["objectives"] = orig_metrics
    moo_config["optimization_options"]["objective_options"]["objectives"].append({"metric": "MSE"})
    controller = Controller(config=moo_config, wrapper=Wrapper)
    controller.setup()

    scheduler = controller.scheduler
    experiment = controller.experiment

    trial = experiment.new_trial(generator_run=scheduler.generation_strategy.gen(experiment))
    for name, metric in experiment.metrics.items():
        metric.fetch_trial_data(trial)

    assert "not returned by fetch_all_trial_data" in caplog.text


def test_metric_fetch_trial_data_works_with_wrapper_fetch_trial_data_single_and_test_sem_passing(moo_config, tmp_path):
    controller = Controller(config=moo_config, wrapper=Wrapper)
    controller.setup(fetch_all=False, experiment_dir=tmp_path)

    scheduler = controller.scheduler
    experiment = controller.experiment
    wrapper = controller.wrapper

    prev_f_ret = None
    for _ in range(5):
        trial = experiment.new_trial(generator_run=scheduler.generation_strategy.gen(experiment))
        for name, metric in experiment.metrics.items():
            ok = metric.fetch_trial_data(trial)
            data = ok.value
            kw = wrapper.fetch_trial_data_single(trial, {}, name)
            sem = kw.pop("sem", None)
            f_ret = metric.f(**kw)
            assert f_ret == data.df["mean"].iloc[0]

            if sem:
                assert data.df["sem"].iloc[0] == sem

            assert f_ret != prev_f_ret
            prev_f_ret = f_ret
