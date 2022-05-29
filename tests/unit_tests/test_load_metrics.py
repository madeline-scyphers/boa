from optiwrap import (
    get_metric_by_class_name,
    get_metric_from_config,
    setup_synthetic_metric,
)


def test_load_metric_by_name():
    metric_synth = setup_synthetic_metric("hartmann4")
    assert metric_synth.name == "Hartmann4"
    assert metric_synth.metric_to_eval.func.name == "FromBotorch_Hartmann4"

    metric_synth = setup_synthetic_metric("hartmann4", name="something")
    assert metric_synth.name == "something"
    assert metric_synth.metric_to_eval.func.name == "FromBotorch_Hartmann4"

    metric_sklearn = get_metric_by_class_name("MSE")
    assert metric_sklearn.name == "mean_squared_error"
    assert metric_sklearn.metric_to_eval.func.__name__ == "mean_squared_error"

    metric_sklearn = get_metric_by_class_name("MSE", name="something")
    assert metric_sklearn.name == "something"
    assert metric_sklearn.metric_to_eval.func.__name__ == "mean_squared_error"


def test_load_metric_from_config(synth_optimization_options, metric_optimization_options):
    metric = get_metric_from_config(synth_optimization_options["metric"])
    assert metric.name == "Hartmann4"
    assert metric.metric_to_eval.func.name == "FromBotorch_Hartmann4"

    metric = get_metric_from_config(metric_optimization_options["metric"])
    assert metric.name == "root_mean_squared_error"
    assert metric.metric_to_eval.func.__name__ == "mean_squared_error"
