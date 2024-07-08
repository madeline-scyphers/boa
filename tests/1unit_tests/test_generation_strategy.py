from ax.modelbridge.generation_strategy import GenerationStep, GenerationStrategy
from ax.modelbridge.registry import Models

from boa import (
    Controller,
    ScriptWrapper,
    WrappedJobRunner,
    get_experiment,
    get_generation_strategy,
)
from boa.utils import check_min_package_version


def test_gen_steps_from_config(gen_strat1_config):
    gs1 = get_generation_strategy(gen_strat1_config)

    gs2 = GenerationStrategy(
        steps=[
            GenerationStep(model=Models.SOBOL, num_trials=5),
            GenerationStep(model=Models.GPEI, num_trials=-1),
        ],
    )
    # we call repr to ensure that the generation strategy is correctly initialized
    # because in ax 0.3.6, GS dynamically adds an attribute to the GS object
    # So, we can't directly compare the objects yet, because their __dict__ size will change
    # during runtime and raise a RuntimeError
    # Stupid I know, as of 2024-07-05 they still haven't merged the PR to fix this
    repr(gs1)
    repr(gs2)

    assert gs1 == gs2


def test_auto_gen_use_saasbo(saasbo_config, tmp_path):
    controller = Controller(config=saasbo_config, wrapper=ScriptWrapper(config=saasbo_config, experiment_dir=tmp_path))
    exp = get_experiment(
        config=controller.config, runner=WrappedJobRunner(wrapper=controller.wrapper), wrapper=controller.wrapper
    )
    gs = get_generation_strategy(config=controller.config, experiment=exp)
    if check_min_package_version("ax-platform", "0.3.5"):
        assert "SAASBO" in gs.name
    else:
        assert "FullyBayesian" in gs.name
