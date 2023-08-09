from ax.modelbridge.generation_strategy import GenerationStep, GenerationStrategy
from ax.modelbridge.registry import Models

from boa import get_generation_strategy


def test_gen_steps_from_config(gen_strat1_config):
    gs1 = get_generation_strategy(gen_strat1_config)

    gs2 = GenerationStrategy(
        steps=[
            GenerationStep(model=Models.SOBOL, num_trials=5),
            GenerationStep(model=Models.GPEI, num_trials=-1),
        ],
    )
    assert gs1 == gs2
