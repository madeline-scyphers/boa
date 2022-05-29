import json
import logging

import yaml

logger = logging.getLogger(__name__)


def _metric_from_jsonlike(data, path_to_data):
    for key in path_to_data:
        try:
            data = data[key]
        except (IndexError, KeyError, TypeError) as e:
            if len(e.args) >= 1:
                e.args = (
                    e.args[0] + "\nCan't load data from file because path to data is invalid!",
                ) + e.args[1:]
            raise
    return data


def metric_from_json(filename, path_to_data, **kwargs):
    with open(filename, "r") as f:
        data = json.load(f)

    return _metric_from_jsonlike(data, path_to_data)


def metric_from_yaml(filename, path_to_data, **kwargs):
    with open(filename, "r") as f:
        data = yaml.safe_load(f)

    return _metric_from_jsonlike(data, path_to_data)
