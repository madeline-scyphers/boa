"""
########################
Saving and Loading
########################

Functions for saving and loading your experiment to
stop and restart.

"""

import json
import logging
import os
from typing import Any, Callable, Dict, Optional, Type

from ax.service.scheduler import Scheduler, SchedulerOptions
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

from boa.metrics.modular_metric import ModularMetric
from boa.runner import WrappedJobRunner

logger = logging.getLogger(__name__)


def scheduler_to_json_file(scheduler, filepath: os.PathLike = "scheduler_snapshot.json") -> None:
    """Save a JSON-serialized snapshot of this `AxClient`'s settings and state
    to a .json file by the given path.
    """
    with open(filepath, "w+") as file:  # pragma: no cover
        file.write(json.dumps(scheduler_to_json_snapshot(scheduler)))
        logger.info(f"Saved JSON-serialized state of optimization to `{filepath}`.")


def scheduler_from_json_file(filepath: os.PathLike = "scheduler.json", wrapper=None, **kwargs) -> Scheduler:
    """Restore an `AxClient` and its state from a JSON-serialized snapshot,
    residing in a .json file by the given path.
    """
    with open(filepath, "r") as file:  # pragma: no cover
        serialized = json.loads(file.read())
        scheduler = scheduler_from_json_snapshot(serialized=serialized, **kwargs)
    if wrapper is not None:
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
    """Serialize this `AxClient` to JSON to be able to interrupt and restart
    optimization and save it to file by the provided path.

    Returns:
        A JSON-safe dict representation of this `AxClient`.
    """
    if encoder_registry is None:
        encoder_registry = CORE_ENCODER_REGISTRY

    if class_encoder_registry is None:
        class_encoder_registry = CORE_CLASS_ENCODER_REGISTRY

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
            scheduler.options,
            encoder_registry=encoder_registry,
            class_encoder_registry=class_encoder_registry,
        ),
    }


def scheduler_from_json_snapshot(
    serialized: Dict[str, Any],
    decoder_registry: Optional[Dict[str, Type]] = None,
    class_decoder_registry: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None,
    **kwargs,
) -> Scheduler:
    """Recreate an `AxClient` from a JSON snapshot."""
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

    ax_client = Scheduler(generation_strategy=generation_strategy, experiment=experiment, options=options, **kwargs)
    ax_client._experiment = experiment
    return ax_client
