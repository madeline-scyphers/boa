"""
########################
Saving and Loading
########################

Helpers for saving and loading BOA Ax Client runs.
"""
from __future__ import annotations

import pathlib
from typing import Any, Optional

from boa.client import BOAClient
from boa.definitions import PathLike
from boa.logger import get_logger
from boa.metrics.modular_metric import ModularMetric
from boa.wrappers.base_wrapper import BaseWrapper

logger = get_logger()


def _reattach_wrapper(client: BOAClient, wrapper: BaseWrapper | None) -> BOAClient:
    if wrapper is None:
        return client
    client.wrapper = wrapper
    runner = getattr(client.experiment, "runner", None)
    if runner is not None and hasattr(runner, "wrapper"):
        runner.wrapper = wrapper
    for metric in client.experiment.metrics.values():
        if isinstance(metric, ModularMetric):
            metric.wrapper = wrapper
    return client


def client_to_json_file(client: BOAClient, client_filepath: PathLike = "client.json", dir_: PathLike = None) -> None:
    """Save BOA Client state to an Ax Client JSON file."""

    client_filepath = pathlib.Path(client_filepath)
    if dir_:
        client_filepath = pathlib.Path(dir_) / client_filepath
    client.client_filepath = client_filepath
    client.save_to_json_file(filepath=str(client.client_filepath))
    logger.info(f"Saved JSON-serialized state of optimization to `{client.client_filepath}`.")


def client_from_json_file(
    filepath: PathLike = "client.json",
    wrapper: Optional[BaseWrapper] = None,
    **kwargs: Any,
) -> BOAClient:
    """Restore a BOA Client from an Ax Client JSON file."""

    client = BOAClient.load_from_json_file(filepath=str(filepath), **kwargs)
    client.client_filepath = pathlib.Path(filepath)
    return _reattach_wrapper(client=client, wrapper=wrapper)


def client_to_csv(
    client: BOAClient,
    opt_filepath: PathLike = "optimization.csv",
    dir_: PathLike = None,
    *,
    metrics_to_end: bool = False,
    **kwargs: Any,
) -> pathlib.Path:
    opt_filepath = pathlib.Path(opt_filepath)
    if dir_:
        opt_filepath = pathlib.Path(dir_) / opt_filepath
    df = client.summarize()
    if metrics_to_end:
        metrics = list(client.experiment.metrics.keys())
        metric_cols = [col for col in df.columns if col in metrics]
        df = df[[col for col in df.columns if col not in metric_cols] + metric_cols]
    kwargs.setdefault("na_rep", "NA")
    df.to_csv(path_or_buf=opt_filepath, index=False, **kwargs)
    logger.info(f"Saved optimization parameterization and objective to `{opt_filepath}`.")
    client.optimization_csv = opt_filepath
    return opt_filepath


def dump_client_data(client: BOAClient, client_filepath: PathLike, opt_filepath: PathLike, **kwargs: Any) -> None:
    client_to_csv(client, opt_filepath=opt_filepath, **kwargs)
    client_to_json_file(client, client_filepath=client_filepath)
