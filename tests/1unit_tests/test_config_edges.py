from io import StringIO

import pytest
from ruamel.yaml import YAML
from botorch.acquisition.analytic import PosteriorMean
from botorch.models.gp_regression import SingleTaskGP
from gpytorch.kernels import RBFKernel
from gpytorch.mlls.exact_marginal_log_likelihood import ExactMarginalLogLikelihood

from boa.config.config import (
    BOAConfig,
    BOAGenerationStrategy,
    BOAMetric,
    BOAObjective,
    BOAOptimization,
    BOAScriptOptions,
    MetricType,
    _model_name_from_reverse_registry,
    add_comment_recurse,
    generate_default_doc_config,
    strip_white_space,
    update_dict,
)
from boa.metrics.metrics import PassThroughMetric
from boa import cd_and_cd_back


def test_boa_metric_validation_aliases_and_instantiated_metrics():
    metric = PassThroughMetric(name="original")
    config = BOAMetric(metric=metric, name="renamed")

    assert config.metric_type == MetricType.INSTANTIATED
    assert metric.name == "renamed"
    assert config.name == "renamed"
    assert BOAMetric(metric="loss", lower_is_better=False).minimize is False
    assert BOAMetric(name="passthrough_only").metric_type == MetricType.PASSTHROUGH
    with pytest.raises(TypeError):
        BOAMetric(metric="x", lower_is_better=True, minimize=False)
    with pytest.raises(TypeError):
        BOAMetric()


def test_optimization_metric_conversion_accepts_none_strings_and_existing_metrics():
    metric = BOAMetric(metric="explicit", metric_type="passthrough")
    optimization = BOAOptimization(
        objective="a + b + explicit",
        metrics={"a": {}, "b": "Mean", "explicit": metric},
        tracking_metrics=["tracked"],
    )

    assert optimization.metrics["a"].metric == "a"
    assert optimization.metrics["b"].metric == "Mean"
    assert optimization.metrics["explicit"] is metric
    assert optimization.tracking_metrics == ["tracked"]
    assert BOAOptimization(objective="score", metrics=None).metrics == {}


def test_generation_strategy_resolves_registered_model_and_acquisition_classes():
    generation_strategy = BOAGenerationStrategy(
        method="custom",
        initialization_budget=3,
        model_config={
            "botorch_model_class": "SingleTaskGP",
            "mll_class": "ExactMarginalLogLikelihood",
            "covar_module_class": "RBFKernel",
        },
        botorch_acqf_class="PosteriorMean",
    )

    assert generation_strategy.model_config.botorch_model_class is SingleTaskGP
    assert generation_strategy.model_config.mll_class is ExactMarginalLogLikelihood
    assert generation_strategy.model_config.covar_module_class is RBFKernel
    assert generation_strategy.botorch_acqf_class is PosteriorMean
    assert _model_name_from_reverse_registry(PosteriorMean) == "PosteriorMean"
    with pytest.raises(ValueError):
        BOAGenerationStrategy(method="custom", botorch_acqf_class="NoSuchAcquisition")


def test_legacy_objective_weight_conversion_and_errors():
    objective = BOAObjective(
        metrics=[
            {"metric": "m1", "metric_type": "passthrough"},
            {"metric": "m2", "metric_type": "passthrough"},
        ],
        weights=[1.0, -0.5],
        minimize=True,
    )

    assert objective.metric_names == ["m1", "m2"]
    assert [metric.weight for metric in objective.metrics] == [1.0, -0.5]
    with pytest.raises(TypeError):
        BOAObjective(metrics=[{"metric": "m1"}], weights=[1, 2])
    with pytest.raises(TypeError):
        BOAObjective(metrics=[{"metric": "m1", "weight": 1.0}], weights=[1.0])


def test_script_options_path_resolution_and_error_branches(tmp_path):
    with pytest.raises(TypeError):
        BOAScriptOptions(run_cmd="echo one", run_model="echo two")
    with pytest.raises(TypeError):
        BOAScriptOptions(rel_to_config=True, rel_to_launch=True)
    with pytest.raises(TypeError):
        BOAScriptOptions(base_path=None, rel_to_config=True)

    with cd_and_cd_back(tmp_path):
        options = BOAScriptOptions(base_path=None, rel_to_config=False, wrapper_path="wrapper.py", rel_to_launch=True)

    assert options.base_path == tmp_path
    assert options.wrapper_path == tmp_path / "wrapper.py"
    assert BOAScriptOptions(run_cmd="echo hi").run_model == "echo hi"


def test_boa_config_ax1_run_metadata_mapping_and_errors():
    config = BOAConfig(
        optimization={"objective": "metric"},
        parameters={"x": {"type": "range", "bounds": [0, 1], "parameter_type": "float"}},
        orchestrator={"n_trials": 4, "total_trials": 10},
    )

    assert config.n_trials == 4
    assert config.trials == 4
    assert config.orchestrator.total_trials == 10
    with pytest.raises(TypeError):
        BOAConfig(optimization={"objective": "metric"}, parameters={}, scheduler={})

    params = {
        "outer": {"x": {"type": "range", "bounds": [0, 1]}},
        "nested": [{"inner": {"y": {"type": "fixed", "value": 1}}}],
    }
    normalized, mapping = BOAConfig.wpr_params_to_boa(params, [["outer"], ["nested", 0, "inner"]])
    restored = BOAConfig.boa_params_to_wpr(
        {"outer_x": 0.5, "nested_0_inner_y": 1},
        mapping,
        from_trial=True,
    )

    assert set(normalized) == {"outer_x", "nested_0_inner_y"}
    assert restored["outer"]["x"] == 0.5
    assert restored["nested"][0]["inner"]["y"] == 1
    with pytest.raises(TypeError):
        BOAConfig.wpr_params_to_boa({"x": {"a": {}}}, [object()])
    with pytest.raises(TypeError):
        BOAConfig.wpr_params_to_boa({"x": {"0": {"a": {}}}}, [["x", 0]])


def test_deprecated_config_conversion_and_default_doc_helpers():
    deprecated = {
        "optimization_options": {
            "objective_options": {
                "objectives": [{"metric": "metric"}],
                "weights": [1.0],
            },
            "generation_strategy": {"method": "fast"},
            "n_trials": 3,
            "experiment": {"name": "old_name"},
        },
        "parameters": {"x": {"type": "range", "bounds": [0, 1], "parameter_type": "float"}},
    }

    converted = BOAConfig.convert_deprecated(deprecated)

    assert converted["objective"]["metrics"][0]["weight"] == 1.0
    assert converted["scheduler"]["n_trials"] == 3
    assert converted["script_options"]["exp_name"] == "old_name"
    with pytest.raises(ValueError):
        BOAConfig.convert_deprecated(
            {
                "optimization_options": {
                    "objective_options": {"objectives": [{"metric": "m1"}], "weights": [1, 2]}
                }
            }
        )

    doc_config, config = generate_default_doc_config()
    assert "optimization" in doc_config
    yaml = YAML()
    stream = StringIO()
    yaml.dump(config.to_dict(), stream)
    commented_map = yaml.load(stream.getvalue())
    doc_with_comments = add_comment_recurse(commented_map, config=config)
    assert "optimization" in doc_with_comments
    assert strip_white_space("  a\n  b", strip_all=False) == "a\nb"
    original = {"a": {"b": 1}, "c": 2}
    update_dict(original, {"a": {"d": 3}, "c": 4})
    assert original == {"a": {"b": 1, "d": 3}, "c": 4}
