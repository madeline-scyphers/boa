from ax.modelbridge.generation_strategy import GenerationStep, GenerationStrategy
from ax.modelbridge.registry import Models

from boa import (
    Controller,
    ScriptWrapper,
    WrappedJobRunner,
    get_experiment,
    get_generation_strategy,
)


def test_gen_steps_from_config(gen_strat1_config):
    gs1 = get_generation_strategy(gen_strat1_config)

    gs2 = GenerationStrategy(
        steps=[
            GenerationStep(model=Models.SOBOL, num_trials=5),
            GenerationStep(model=Models.GPEI, num_trials=-1),
        ],
    )
    assert gs1 == gs2


def test_auto_gen_use_saasbo(saasbo_config, tmp_path):
    controller = Controller(config=saasbo_config, wrapper=ScriptWrapper(config=saasbo_config, experiment_dir=tmp_path))
    exp = get_experiment(
        config=controller.config, runner=WrappedJobRunner(wrapper=controller.wrapper), wrapper=controller.wrapper
    )
    gs = get_generation_strategy(config=controller.config, experiment=exp)
    if "SAASBO" in Models.__members__:  # newer versions of Ax use SAASBO as model name
        assert "SAASBO" in gs.name
    else:
        assert "FullyBayesian" in gs.name
