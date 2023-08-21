"""
########################
Saving and Loading
########################

Functions for saving and loading your experiment to
stop and restart.

"""

import json
import pathlib
from copy import deepcopy
from dataclasses import asdict
from typing import Any, Callable, Dict, Optional, Type

from ax.exceptions.storage import JSONDecodeError as AXJSONDecodeError
from ax.exceptions.storage import JSONEncodeError as AXJSONEncodeError
from ax.service.scheduler import SchedulerOptions
from ax.service.utils.report_utils import exp_to_df
from ax.storage.json_store.decoder import (
    generation_strategy_from_json,
    object_from_json,
)
from ax.storage.json_store.encoder import object_to_json
from ax.storage.json_store.registry import (
    CORE_CLASS_DECODER_REGISTRY,
    CORE_CLASS_ENCODER_REGISTRY,
    CORE_DECODER_REGISTRY,
    CORE_ENCODER_REGISTRY,
)

from boa.__version__ import __version__
from boa.definitions import PathLike
from boa.logger import get_logger
from boa.metrics.modular_metric import ModularMetric
from boa.runner import WrappedJobRunner
from boa.scheduler import Scheduler
from boa.utils import (
    _load_attr_from_module,
    _load_module_from_path,
    get_dictionary_from_callable,
)
from boa.wrappers.base_wrapper import BaseWrapper
from boa.wrappers.script_wrapper import ScriptWrapper

logger = get_logger()


def scheduler_to_json_file(
    scheduler, scheduler_filepath: PathLike = "scheduler.json", dir_: PathLike = None, **kwargs
) -> None:
    """Save a JSON-serialized snapshot of this `Scheduler`'s settings and state
    to a .json file by the given path.
    """
    if dir_:
        scheduler_filepath = pathlib.Path(dir_) / scheduler_filepath
    with open(scheduler_filepath, "w+") as file:  # pragma: no cover
        file.write(json.dumps(scheduler_to_json_snapshot(scheduler), indent=4))
        logger.info(
            f"Saved JSON-serialized state of optimization to `{scheduler_filepath}`." f"\nBoa version: {__version__}"
        )


def scheduler_from_json_file(filepath: PathLike = "scheduler.json", wrapper=None, **kwargs) -> Scheduler:
    """Restore an `Scheduler` and its state from a JSON-serialized snapshot,
    residing in a .json file by the given path.
    """
    with open(filepath, "r") as file:  # pragma: no cover
        serialized = json.loads(file.read())
        scheduler = scheduler_from_json_snapshot(serialized=serialized, **kwargs)

    wrapper = scheduler.experiment.runner.wrapper

    if wrapper is not None:
        for trial in scheduler.running_trials:
            wrapper.set_trial_status(trial)  # try and complete or fail any leftover trials

        for trial in scheduler.running_trials:  # any trial that was marked above is no longer here
            trial.mark_failed()  # fail anything leftover from above
    return scheduler


def scheduler_to_json_snapshot(
    scheduler: Scheduler,
    encoder_registry: Optional[Dict[Type, Callable[[Any], Dict[str, Any]]]] = None,
    class_encoder_registry: Optional[Dict[Type, Callable[[Any], Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """Serialize this `Scheduler` to JSON to be able to interrupt and restart
    optimization and save it to file by the provided path.

    Returns:
        A JSON-safe dict representation of this `Scheduler`.
    """
    if encoder_registry is None:
        encoder_registry = CORE_ENCODER_REGISTRY

    if class_encoder_registry is None:
        class_encoder_registry = CORE_CLASS_ENCODER_REGISTRY

    options = asdict(scheduler.options)
    options.pop("global_stopping_strategy", None)

    options = SchedulerOptions(**options)

    try:
        wrapper_serialization = object_to_json(
            scheduler.experiment.runner.wrapper,
            encoder_registry=encoder_registry,
            class_encoder_registry=class_encoder_registry,
        )
    except AXJSONEncodeError as e:
        logger.error(e)
        wrapper_serialization = scheduler.experiment.runner.wrapper.to_dict()

    gs = object_to_json(
        scheduler.generation_strategy,
        encoder_registry=encoder_registry,
        class_encoder_registry=class_encoder_registry,
    )

    serialization = {
        "_type": scheduler.__class__.__name__,
        "experiment": object_to_json(
            scheduler.experiment,
            encoder_registry=encoder_registry,
            class_encoder_registry=class_encoder_registry,
        ),
        "generation_strategy": gs,
        "options": object_to_json(
            options,
            encoder_registry=encoder_registry,
            class_encoder_registry=class_encoder_registry,
        ),
        "boa_version": __version__,
    }
    if wrapper_serialization:
        serialization["wrapper"] = wrapper_serialization
    return serialization


def scheduler_from_json_snapshot(
    serialized: Dict[str, Any],
    decoder_registry: Optional[Dict[str, Type]] = None,
    class_decoder_registry: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None,
    wrapper_path=None,
    **kwargs,
) -> Scheduler:
    """Recreate an `Scheduler` from a JSON snapshot."""
    if decoder_registry is None:
        decoder_registry = CORE_DECODER_REGISTRY

    if class_decoder_registry is None:
        class_decoder_registry = CORE_CLASS_DECODER_REGISTRY

    if "options" in serialized:
        options = object_from_json(
            serialized.pop("options"),
            decoder_registry=decoder_registry,
            class_decoder_registry=class_decoder_registry,
        )
    else:
        options = SchedulerOptions()

    experiment = object_from_json(
        serialized.pop("experiment"),
        decoder_registry=decoder_registry,
        class_decoder_registry=class_decoder_registry,
    )

    wrapper = None
    if "wrapper" in serialized:
        wrapper_dict = serialized.pop("wrapper", {})
        config = object_from_json(
            wrapper_dict["config"],
            decoder_registry=decoder_registry,
            class_decoder_registry=class_decoder_registry,
        )
        # sometimes the way people write their to_dict methods wrap it in a list
        if isinstance(wrapper_dict, list) and len(wrapper_dict) == 1:
            wrapper_dict = wrapper_dict[0]

        try:
            wrapper = object_from_json(
                deepcopy(wrapper_dict),
                decoder_registry=decoder_registry,
                class_decoder_registry=class_decoder_registry,
            )
        except Exception as e:
            deserialized = recursive_deserialize(
                wrapper_dict,
                decoder_registry=decoder_registry,
                class_decoder_registry=class_decoder_registry,
            )

            if ("path" in wrapper_dict and pathlib.Path(deserialized["path"]).exists()) or (
                wrapper_path is not None and pathlib.Path(wrapper_path).exists()
            ):

                path = pathlib.Path(wrapper_path) if wrapper_path is not None else pathlib.Path(deserialized["path"])
                try:
                    module = _load_module_from_path(path)
                    WrapperCls: Type[BaseWrapper] = _load_attr_from_module(module, wrapper_dict["name"])
                    wrapper = WrapperCls.from_dict(**{**wrapper_dict, "config": config})
                except Exception:
                    logger.exception(
                        f"Failed to deserialize wrapper because of: {e!r}" f"\n\nUsing basic ScriptWrapper as back up"
                    )
                    wrapper = ScriptWrapper.from_dict(
                        **{**get_dictionary_from_callable(ScriptWrapper.from_dict, wrapper_dict), "config": config}
                    )

            else:
                logger.exception(
                    f"Failed to deserialize wrapper because of: {e!r}" f"\n\nUsing basic ScriptWrapper as back up"
                )
                wrapper = ScriptWrapper.from_dict(**get_dictionary_from_callable(ScriptWrapper.from_dict, wrapper_dict))

    serialized_generation_strategy = serialized.pop("generation_strategy")
    generation_strategy = generation_strategy_from_json(
        generation_strategy_json=serialized_generation_strategy, experiment=experiment
    )

    generation_strategy._fit_or_update_current_model(data=experiment.fetch_data())

    scheduler = Scheduler(generation_strategy=generation_strategy, experiment=experiment, options=options, **kwargs)
    scheduler._experiment = experiment
    if wrapper:
        if isinstance(scheduler.experiment.runner, WrappedJobRunner):
            scheduler.experiment.runner.wrapper = wrapper
        for metric in scheduler.experiment.metrics.values():
            if isinstance(metric, ModularMetric):
                metric.wrapper = wrapper
    return scheduler


def recursive_deserialize(obj, **kwargs):
    if isinstance(obj, dict):
        try:
            if "__type" not in obj:  # at least this out dict isn't serialized in AX format, let's check inners
                raise AXJSONDecodeError("obj is not a AX JSON deserializable object")
            obj = object_from_json(obj, **kwargs)
        except (AXJSONDecodeError, TypeError):  # TypeError until https://github.com/facebook/Ax/pull/1418 is merged
            for key, value in obj.items():
                obj[key] = recursive_deserialize(value, **kwargs)
    return obj


def exp_opt_to_csv(experiment, opt_path: PathLike = "optimization.csv", dir_: PathLike = None, **kwargs):
    if dir_:
        opt_path = pathlib.Path(dir_) / opt_path
    df = exp_to_df(experiment)
    df.to_csv(path_or_buf=opt_path, index=False, **kwargs)
    logger.info(f"Saved optimization parametrization and objective to `{opt_path}`.")


def scheduler_opt_to_csv(scheduler, **kwargs):
    return exp_opt_to_csv(scheduler.experiment, **kwargs)


def dump_scheduler_data(scheduler, **kwargs):
    scheduler_to_json_file(scheduler, **kwargs)
    scheduler_opt_to_csv(scheduler, **kwargs)
