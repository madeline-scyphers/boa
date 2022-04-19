from __future__ import annotations

from ax import SearchSpace
from ax.service.ax_client import AxClient


import datetime as dt
from pathlib import Path



import click
from ax import Experiment, Objective, OptimizationConfig
from ax.modelbridge.generation_strategy import GenerationStrategy
from ax.modelbridge.dispatch_utils import choose_generation_strategy
from ax.service.scheduler import Scheduler, SchedulerOptions
from ax.core import GenerationStrategy

from optiwrap import (
    instantiate_search_space_from_json,
    MSE,
    WrappedJobRunner,
    make_experiment_dir,
    read_experiment_config
)
from optiwrap.utils import get_dictionary_from_callable


def instantiate_search_space_from_json(
    parameters: list | None = None, parameter_constraints: list | None = None
) -> SearchSpace:
    parameters = parameters if parameters is not None else []
    parameter_constraints = parameter_constraints if parameter_constraints is not None else []
    return AxClient.make_search_space(parameters, parameter_constraints)


def generation_strategy_from_experiment(experiment: Experiment, settings: dict) -> GenerationStrategy:
    return choose_generation_strategy(
        search_space=experiment.search_space,
        **get_dictionary_from_callable(choose_generation_strategy, settings))


def get_Scheduler(experiment: Experiment, generation_strategy: GenerationStrategy, scheduler_options: SchedulerOptions):
    return Scheduler(
        experiment=experiment,
        generation_strategy=generation_strategy,
        options=scheduler_options
    )


def make_fetch_experiment_with_runner_and_metric(
    ex_settings, search_space_params, wrapper
) -> Experiment:

    # Taking command line arguments for path of config file, input data, and output directory

    # use default options if invalid command line arguments are given

    search_space = instantiate_search_space_from_json(search_space_params, [])

    objective = Objective(
        metric=MSE(name=ex_settings["objective_name"], wrapper=wrapper), minimize=True
    )

    return Experiment(
        search_space=search_space,
        optimization_config=OptimizationConfig(objective=objective),
        runner=WrappedJobRunner(wrapper=wrapper),
        # is_test=True,  # Marking this experiment as a test experiment.
        **get_dictionary_from_callable(Experiment.__init__, ex_settings),
    )