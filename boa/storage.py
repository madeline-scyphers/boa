"""
########################
Saving and Loading
########################

Helpers for saving and loading BOA Ax Client runs.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Optional

from boa.client import BOAClient
from boa.definitions import PathLike
from boa.logger import get_logger
from boa.wrappers.base_wrapper import BaseWrapper
from boa.wrappers.wrapper_utils import _load_attr_from_module, _load_module_from_path

logger = get_logger()


def _path_from_json_value(value):
    if isinstance(value, dict) and "pathsegments" in value:
        return pathlib.Path(*value["pathsegments"])
    return pathlib.Path(value)


def _reattach_wrapper(client: BOAClient, wrapper: BaseWrapper | None) -> BOAClient:
    return client.attach_wrapper(wrapper)


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
    wrapper_path: Optional[PathLike] = None,
    wrapper_name: Optional[str] = None,
    **kwargs: Any,
) -> BOAClient:
    """Restore a BOA Client from an Ax Client JSON file."""

    filepath = pathlib.Path(filepath)
    with open(filepath) as file:
        snapshot = json.load(file)
    if snapshot.get("wrapper") is not None:
        experiment_dir = snapshot["wrapper"].get("experiment_dir")
        if experiment_dir is not None and not _path_from_json_value(experiment_dir).exists():
            snapshot["wrapper"]["experiment_dir"] = str(filepath.parent)
    if wrapper_path:
        if wrapper_name is None:
            wrapper_name = snapshot.get("wrapper", {}).get("name")
        module = _load_module_from_path(wrapper_path)
        _load_attr_from_module(module, wrapper_name or "Wrapper")
    client = BOAClient._from_json_snapshot(snapshot=snapshot, storage_config=kwargs.pop("storage_config", None))
    client.client_filepath = filepath
    if client.wrapper is not None and client.wrapper.experiment_dir is not None:
        experiment_dir = pathlib.Path(client.wrapper.experiment_dir)
        if not experiment_dir.exists():
            client.wrapper.experiment_dir = pathlib.Path(filepath).parent
    return _reattach_wrapper(client=client, wrapper=wrapper or client.wrapper)


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
