from boa import (
    BaseWrapper,
    Controller,
    get_metric_by_class_name,
    get_metric_from_config,
    setup_synthetic_metric,
)


class Wrapper(BaseWrapper):
    def set_trial_status(self, trial) -> None:
        trial.mark_completed()

    def fetch_all_trial_data(self, trial, metric_properties, *args, **kwargs):
        return {
            "Meanyyy": {"a": [-0.3691, 4.6544, 1.2675, -0.4327], "sem": 4.5},
            "RMSE": {"y_true": [1.12, 1.25, 2.54, 4.52], "y_pred": [1.51, 1.01, 2.21, 4.50]},
        }


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


# TODO rename when MOO wrapper func name is settled
def test_metric_fetch_trial_data_works_with_wrapper_fetch_all_and_test_sem_passing(moo_config):
    c = Controller(config=moo_config, wrapper=Wrapper)
    c.setup()
    trial = c.experiment.new_trial(generator_run=c.scheduler.generation_strategy.gen(c.experiment))
    for name, metric in c.experiment.metrics.items():
        data = metric.fetch_trial_data(trial)
        sem = c.wrapper._metric_dict[name].pop("sem", None)
        f_ret = metric.f(**c.wrapper._metric_dict[name])
        assert f_ret == data.df["mean"].iloc[0]
        if sem:
            assert data.df["sem"].iloc[0] == sem
