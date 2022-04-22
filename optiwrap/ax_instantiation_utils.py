from __future__ import annotations

from ax import SearchSpace
from ax.service.ax_client import AxClient

from ax import Experiment, Objective, OptimizationConfig
from ax.modelbridge.generation_strategy import GenerationStrategy
from ax.modelbridge.dispatch_utils import choose_generation_strategy
from ax.service.scheduler import Scheduler, SchedulerOptions

from optiwrap.utils import get_dictionary_from_callable
from optiwrap.metrics import get_metric_by_class_name


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
    scheduler_options = scheduler_options or SchedulerOptions()
    if generation_strategy is None:
        generation_strategy = generation_strategy_from_experiment(experiment, config)
    return Scheduler(
        experiment=experiment, generation_strategy=generation_strategy, options=scheduler_options
    )


def get_experiment(
    config: dict,
    runner,
    wrapper=None,
):
    settings = config["optimization_options"]

    search_space = instantiate_search_space_from_json(
        config.get("search_space_parameters"), config.get("search_space_parameter_constraints")
    )

    metric = get_metric_by_class_name(settings["metric_name"])
    objective = Objective(
        metric=metric(name=settings["objective_name"], wrapper=wrapper), minimize=True
    )

    return Experiment(
        search_space=search_space,
        optimization_config=OptimizationConfig(objective=objective),
        runner=runner,
        **get_dictionary_from_callable(Experiment.__init__, settings),
    )
