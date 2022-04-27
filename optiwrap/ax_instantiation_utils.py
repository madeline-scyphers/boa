from __future__ import annotations

from ax import Experiment, Objective, OptimizationConfig, Runner, SearchSpace
from ax.modelbridge.dispatch_utils import choose_generation_strategy
from ax.modelbridge.generation_strategy import GenerationStrategy
from ax.service.ax_client import AxClient
from ax.service.scheduler import Scheduler, SchedulerOptions

from optiwrap.metrics.metrics import get_metric
from optiwrap.utils import get_dictionary_from_callable


def instantiate_search_space_from_json(
    parameters: list | None = None, parameter_constraints: list | None = None
) -> SearchSpace:
    parameters = parameters if parameters is not None else []
    parameter_constraints = parameter_constraints if parameter_constraints is not None else []
    return AxClient.make_search_space(parameters, parameter_constraints)


def generation_strategy_from_experiment(experiment: Experiment, config: dict) -> GenerationStrategy:
    return choose_generation_strategy(
        search_space=experiment.search_space,
        **get_dictionary_from_callable(choose_generation_strategy, config),
    )


def get_scheduler(
    experiment: Experiment,
    generation_strategy: GenerationStrategy = None,
    scheduler_options: SchedulerOptions = None,
    config: dict = None,
):
    scheduler_options = scheduler_options or SchedulerOptions(
        **config["optimization_options"]["scheduler"]
    )
    if generation_strategy is None:
        if ("total_trials" in config["optimization_options"]["scheduler"]
            and "num_trials" not in config["optimization_options"]["generation_strategy"]):
           config["optimization_options"]["generation_strategy"]["num_trials"] = (
               config["optimization_options"]["scheduler"]["total_trials"])
        generation_strategy = generation_strategy_from_experiment(
            experiment, config["optimization_options"]["generation_strategy"])
    return Scheduler(
        experiment=experiment, generation_strategy=generation_strategy, options=scheduler_options
    )


def get_experiment(
    config: dict,
    runner: Runner,
    wrapper=None,
):
    settings = config["optimization_options"]

    search_space = instantiate_search_space_from_json(
        config.get("search_space_parameters"), config.get("search_space_parameter_constraints")
    )

    metric = get_metric(settings["metric"], param_names=list(search_space.parameters))
    objective = Objective(metric=metric(wrapper=wrapper), minimize=True)

    return Experiment(
        search_space=search_space,
        optimization_config=OptimizationConfig(objective=objective),
        runner=runner,
        **get_dictionary_from_callable(Experiment.__init__, settings["experiment"]),
    )
