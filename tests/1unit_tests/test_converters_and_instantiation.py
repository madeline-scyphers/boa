import pytest
from ax.early_stopping.strategies import PercentileEarlyStoppingStrategy
from ax.global_stopping.strategies import ImprovementGlobalStoppingStrategy

from boa.ax_api import OrchestratorOptions, OutcomeConstraint, ScalarizedObjective
from boa.config.config import BOAMetric, BOAObjective
from boa.config.converters import (
    _convert_noton_type,
    _load_stopping_strategy,
    _metric_converter,
    _orchestrator_converter,
    _parameter_normalization,
)


def test_converter_helpers_cover_defaults_and_existing_instances():
    converter = _convert_noton_type(int, int, default_if_none=lambda: 7)

    assert converter(None) == 7
    assert converter("5") == 5
    assert converter(3) == 3

    metric = BOAMetric(metric="metric")
    assert _metric_converter([{"metric": "other"}, metric])[1] is metric
    assert _convert_noton_type(str, str, default_if_none="fallback")(None) == "fallback"
    assert _parameter_normalization([{"name": "x"}]) == [{"name": "x"}]
    assert _parameter_normalization({"x": 3}) == [{"value": 3, "type": "fixed", "name": "x"}]
    assert _parameter_normalization({"x": {"type": "range", "bounds": [0, 1], "value": 0.5}}) == [
        {"type": "range", "bounds": [0, 1], "name": "x"}
    ]
    assert _parameter_normalization({"x": {"type": "fixed", "bounds": [0, 1], "value": 0.5}}) == [
        {"type": "fixed", "value": 0.5, "name": "x"}
    ]


def test_stopping_strategy_converters_create_ax_options():
    early = _load_stopping_strategy(
        {"type": "PercentileEarlyStoppingStrategy", "percentile_threshold": 50, "min_progression": 1},
        module=__import__("ax.early_stopping.strategies", fromlist=["unused"]),
    )

    options = _orchestrator_converter(
        {
            "total_trials": 5,
            "early_stopping_strategy": early,
            "global_stopping_strategy": {
                "type": "improvement",
                "min_trials": 2,
                "window_size": 1,
                "improvement_bar": 0.1,
            },
        }
    )

    assert isinstance(options, OrchestratorOptions)
    assert isinstance(options.early_stopping_strategy, PercentileEarlyStoppingStrategy)
    assert isinstance(options.global_stopping_strategy, ImprovementGlobalStoppingStrategy)
    with pytest.raises(ValueError):
        _load_stopping_strategy(
            {"percentile_threshold": 50},
            module=__import__("ax.early_stopping.strategies", fromlist=["unused"]),
        )
    assert _load_stopping_strategy(None, module=__import__("ax.early_stopping.strategies", fromlist=["unused"])) is None
