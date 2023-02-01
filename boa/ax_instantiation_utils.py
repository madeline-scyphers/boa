"""
###################################
Ax Instantiation Utility Functions
###################################

Utility functions to instantiate Ax objects

"""

from __future__ import annotations

import copy
import time

from ax import Experiment, Runner, SearchSpace
from ax.modelbridge.dispatch_utils import choose_generation_strategy
from ax.modelbridge.generation_strategy import GenerationStep, GenerationStrategy
from ax.modelbridge.registry import Models
from ax.modelbridge.torch import TorchModelBridge
from ax.models.torch.botorch_moo import MultiObjectiveBotorchModel
from ax.service.scheduler import SchedulerOptions

from boa.instantiation_base import BoaInstantiationBase
from boa.logger import get_logger
from boa.scheduler import Scheduler
from boa.utils import get_dictionary_from_callable
from boa.wrappers.base_wrapper import BaseWrapper

logger = get_logger()


def instantiate_search_space_from_json(
    parameters: list | None = None, parameter_constraints: list | None = None
) -> SearchSpace:
    parameters = parameters if parameters is not None else []
    parameter_constraints = parameter_constraints if parameter_constraints is not None else []
    return BoaInstantiationBase.make_search_space(parameters, parameter_constraints)


def get_generation_strategy(config: dict, experiment: Experiment = None, **kwargs):
    if config.get("steps"):  # if they are explicitly defining the steps, use those to make gen strat
        return generation_strategy_from_config(config=config, experiment=experiment)
    # else auto generate the gen strat
    return choose_generation_strategy_from_experiment(experiment=experiment, config=config, **kwargs)


def generation_strategy_from_config(config: dict, experiment: Experiment = None):
    config_ = copy.deepcopy(config)
    for i, step in enumerate(config_["steps"]):
        try:
            step["model"] = Models[step["model"]]
        except KeyError:
            step["model"] = Models(step["model"])
        config_["steps"][i] = GenerationStep(**step)

    gs = GenerationStrategy(**get_dictionary_from_callable(GenerationStrategy.__init__, config_))
    if experiment:
        gs.experiment = experiment
    return gs


def choose_generation_strategy_from_experiment(experiment: Experiment, config: dict, **kwargs) -> GenerationStrategy:
    return choose_generation_strategy(
        search_space=experiment.search_space,
        experiment=experiment,
        optimization_config=experiment.optimization_config,
        **{**get_dictionary_from_callable(choose_generation_strategy, config), **kwargs},
    )


def get_scheduler(
    experiment: Experiment,
    generation_strategy: GenerationStrategy = None,
    scheduler_options: SchedulerOptions = None,
    config: dict = None,
    **kwargs,
) -> Scheduler:
    scheduler_options = scheduler_options or SchedulerOptions(**config["optimization_options"]["scheduler"])
    if generation_strategy is None:
        if (
            "total_trials" in config["optimization_options"]["scheduler"]
            and "num_trials" not in config["optimization_options"]["generation_strategy"]
        ):
            config["optimization_options"]["generation_strategy"]["num_trials"] = config["optimization_options"][
                "scheduler"
            ]["total_trials"]
        generation_strategy = get_generation_strategy(
            config=config["optimization_options"]["generation_strategy"], experiment=experiment
        )

        _check_moo_has_right_aqf_mode_bridge_cls(experiment, generation_strategy)
    # db_settings = DBSettings(
    #     url="sqlite:///foo.db",
    #     decoder=Decoder(config=SQAConfig()),
    #     encoder=Encoder(config=SQAConfig()),
    # )

    # init_engine_and_session_factory(url=db_settings.url)
    # engine = get_engine()
    # create_all_tables(engine)

    return Scheduler(
        experiment=experiment,
        generation_strategy=generation_strategy,
        options=scheduler_options,
        # db_settings=db_settings,
    )


def get_experiment(config: dict, runner: Runner, wrapper: BaseWrapper = None, **kwargs):
    opt_options = config["optimization_options"]

    search_space = instantiate_search_space_from_json(config.get("parameters"), config.get("parameter_constraints"))

    info_only_metrics = BoaInstantiationBase.get_metrics_from_obj_config(
        **opt_options["objective_options"], info_only=True
    )

    optimization_config = BoaInstantiationBase.make_optimization_config(
        **get_dictionary_from_callable(BoaInstantiationBase.make_optimization_config, opt_options["objective_options"]),
        wrapper=wrapper,
    )

    if "name" not in opt_options["experiment"]:
        if "name" in opt_options:
            opt_options["experiment"]["name"] = opt_options["name"]
        else:
            opt_options["experiment"]["name"] = time.time()

    exp = Experiment(
        search_space=search_space,
        optimization_config=optimization_config,
        runner=runner,
        tracking_metrics=info_only_metrics,
        **get_dictionary_from_callable(Experiment.__init__, opt_options["experiment"]),
    )
    # we use getattr here in case someone subclassed without the proper super calls
    if not getattr(wrapper, "metric_names", None):
        wrapper.metric_names = list(exp.metrics.keys())
    return exp


def _check_moo_has_right_aqf_mode_bridge_cls(experiment, generation_strategy):
    if experiment.is_moo_problem:
        for step in generation_strategy._steps:
            model_bridge = step.model.model_bridge_class
            is_moo_modelbridge = (
                model_bridge and issubclass(model_bridge, TorchModelBridge) and experiment.is_moo_problem
            )
            if is_moo_modelbridge and not isinstance(model_bridge, MultiObjectiveBotorchModel):
                logger.warning(
                    "Multi Objective Optimization was specified,"
                    f"\nbut generation steps used step: {step}, which is not"
                    f" a MOO generation step."
                )
