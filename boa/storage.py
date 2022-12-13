"""
########################
Saving and Loading
########################

Functions for saving and loading your experiment to
stop and restart.

"""

import json
from dataclasses import asdict
from typing import Any, Callable, Dict, Optional, Type

from ax.service.scheduler import SchedulerOptions
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

from boa.definitions import PathLike
from boa.logger import get_logger
from boa.metrics.modular_metric import ModularMetric
from boa.runner import WrappedJobRunner
from boa.scheduler import Scheduler
from boa.wrappers.wrapper_utils import initialize_wrapper

logger = get_logger(__name__)


def scheduler_to_json_file(scheduler, filepath: PathLike = "scheduler_snapshot.json") -> None:
    """Save a JSON-serialized snapshot of this `Scheduler`'s settings and state
    to a .json file by the given path.
    """
    with open(filepath, "w+") as file:  # pragma: no cover
        file.write(json.dumps(scheduler_to_json_snapshot(scheduler)))
        logger.info(f"Saved JSON-serialized state of optimization to `{filepath}`.")


def scheduler_from_json_file(filepath: PathLike = "scheduler.json", wrapper=None, **kwargs) -> Scheduler:
    """Restore an `Scheduler` and its state from a JSON-serialized snapshot,
    residing in a .json file by the given path.
    """
    with open(filepath, "r") as file:  # pragma: no cover
        serialized = json.loads(file.read())
        scheduler = scheduler_from_json_snapshot(serialized=serialized, **kwargs)
    wrapper_dict = serialized.pop("wrapper", {})
    wrapper_dict = object_from_json(wrapper_dict)
    if not wrapper and "path" in wrapper_dict:
        wrapper = initialize_wrapper(wrapper=wrapper_dict["path"], wrapper_name=wrapper_dict["name"], **wrapper_dict)
        wrapper.config = wrapper_dict.get("config", {})
        wrapper.experiment_dir = wrapper_dict.get("experiment_dir")
        wrapper.working_dir = wrapper_dict.get("working_dir")
        wrapper.output_dir = wrapper_dict.get("output_dir")
        wrapper.metric_names = wrapper_dict.get("metric_names")

    if wrapper is not None:
        for trial in scheduler.running_trials:
            wrapper.set_trial_status(trial)  # try and complete or fail and leftover trials

        for trial in scheduler.running_trials:  # any trial that was marked above is no longer here
            trial.mark_failed()  # fail anything leftover from above
        if isinstance(scheduler.experiment.runner, WrappedJobRunner):
            scheduler.experiment.runner.wrapper = wrapper
        for metric in scheduler.experiment.metrics.values():
            if isinstance(metric, ModularMetric):
                metric.wrapper = wrapper
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

    return {
        "_type": scheduler.__class__.__name__,
        "experiment": object_to_json(
            scheduler.experiment,
            encoder_registry=encoder_registry,
            class_encoder_registry=class_encoder_registry,
        ),
        "generation_strategy": object_to_json(
            scheduler.generation_strategy,
            encoder_registry=encoder_registry,
            class_encoder_registry=class_encoder_registry,
        ),
        "options": object_to_json(
            options,
            encoder_registry=encoder_registry,
            class_encoder_registry=class_encoder_registry,
        ),
        "wrapper": scheduler.experiment.runner.wrapper.to_dict(),
    }


def scheduler_from_json_snapshot(
    serialized: Dict[str, Any],
    decoder_registry: Optional[Dict[str, Type]] = None,
    class_decoder_registry: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None,
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

    serialized_generation_strategy = serialized.pop("generation_strategy")
    generation_strategy = generation_strategy_from_json(
        generation_strategy_json=serialized_generation_strategy, experiment=experiment
    )

    scheduler = Scheduler(generation_strategy=generation_strategy, experiment=experiment, options=options, **kwargs)
    scheduler._experiment = experiment
    return scheduler
