"""
###################################
Ax Instantiation Utility Functions
###################################

Utility functions to instantiate Ax objects

"""

from __future__ import annotations

from typing import Optional

from ax import Experiment, Runner, SearchSpace
from ax.modelbridge.dispatch_utils import choose_generation_strategy
from ax.modelbridge.generation_strategy import GenerationStrategy
from ax.modelbridge.torch import TorchModelBridge
from ax.models.torch.botorch_moo import MultiObjectiveBotorchModel
from ax.service.utils.instantiation import TParameterRepresentation

from boa.config import BOAConfig
from boa.instantiation_base import BoaInstantiationBase
from boa.logger import get_logger
from boa.scheduler import Scheduler
from boa.wrappers.base_wrapper import BaseWrapper

logger = get_logger()


def instantiate_search_space_from_json(
    parameters: list[TParameterRepresentation] = None, parameter_constraints: Optional[list[str]] = None
) -> SearchSpace:
    parameters = parameters if parameters is not None else []
    parameter_constraints = parameter_constraints if parameter_constraints is not None else []
    return BoaInstantiationBase.make_search_space(parameters, parameter_constraints)


def get_generation_strategy(config: BOAConfig, experiment: Experiment = None, **kwargs):
    if config.generation_strategy.get("steps"):
        generation_strategy = GenerationStrategy(steps=config.generation_strategy["steps"])
    else:
        if config.trials:
            kwargs["num_trials"] = config.trials
        generation_strategy = choose_generation_strategy_from_experiment(experiment=experiment, config=config, **kwargs)
    return generation_strategy


def choose_generation_strategy_from_experiment(
    experiment: Experiment, config: BOAConfig, **kwargs
) -> GenerationStrategy:
    return choose_generation_strategy(
        search_space=experiment.search_space,
        experiment=experiment,
        optimization_config=experiment.optimization_config,
        **config.generation_strategy,
    )


def get_scheduler(
    experiment: Experiment,
    config: BOAConfig = None,
    **kwargs,
) -> Scheduler:
    generation_strategy = get_generation_strategy(config=config, experiment=experiment, **kwargs)

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
        options=config.scheduler,
        # db_settings=db_settings,
    )


def get_experiment(config: BOAConfig, runner: Runner, wrapper: BaseWrapper = None, **kwargs):

    search_space = instantiate_search_space_from_json(config.parameters, config.parameter_constraints)

    info_only_metrics = BoaInstantiationBase.get_metrics_from_obj_config(
        config.objective, wrapper=wrapper, info_only=True
    )

    optimization_config = BoaInstantiationBase.make_optimization_config(
        config.objective,
        wrapper=wrapper,
    )

    exp = Experiment(
        search_space=search_space,
        optimization_config=optimization_config,
        runner=runner,
        tracking_metrics=info_only_metrics,
        name=config.name,
    )
    # we use getattr here in case someone subclassed without the proper super calls
    if not getattr(wrapper, "metric_names", None):
        wrapper.metric_names = list(exp.metrics.keys())
    return exp


def _check_moo_has_right_aqf_mode_bridge_cls(experiment, generation_strategy):
    if experiment.is_moo_problem:
        for step in generation_strategy._steps:
            model_bridge = step.model.model_bridge_class
            model_cls = step.model.model_class
            is_moo_modelbridge = (
                model_bridge and issubclass(model_bridge, TorchModelBridge) and experiment.is_moo_problem
            )
            if is_moo_modelbridge and not (
                isinstance(model_bridge, MultiObjectiveBotorchModel)
                or issubclass(model_cls, MultiObjectiveBotorchModel)
            ):
                logger.warning(
                    "Multi Objective Optimization was specified,"
                    f"\nbut generation steps used step: {step}, which is not"
                    f" a MOO generation step."
                )
