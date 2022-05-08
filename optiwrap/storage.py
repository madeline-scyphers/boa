import os
from pathlib import Path
import pickle
import logging

from ax import Experiment
from ax.exceptions.storage import JSONEncodeError
from ax.storage.json_store.save import save_experiment as ax_save_experiment
from ax.storage.json_store.load import load_experiment as ax_load_experiment


logger = logging.getLogger(__name__)


def save_experiment(experiment: Experiment, filepath: os.PathLike, *args, **kwargs):
    try:
        ax_save_experiment(experiment, filepath, *args, **kwargs)
    except JSONEncodeError:
        logger.warning("Failed to serialize experiment to JSON, attempting to pickle")
        with open(Path(str(filepath) + ".pickle") , 'wb') as f:
            pickle.dump(experiment, f)
        logger.warning("Pickling succeeded. Experiment Pickled to %s" % Path(str(filepath) + ".pickle"))


def load_experiment(
    filepath: str, *args, **kwargs) -> Experiment:
    """Load experiment from file.

    1) Read file.
    2) Convert dictionary to Ax experiment instance.
    """
    try:
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    except pickle.UnpicklingError:
        return ax_load_experiment(filepath, *args, **kwargs)
