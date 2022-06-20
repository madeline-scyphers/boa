import logging
import traceback
from abc import ABCMeta
from functools import wraps
from unittest.mock import MagicMock

from ax.storage.json_store.encoders import runner_to_dict
from ax.storage.json_store.registry import CORE_DECODER_REGISTRY, CORE_ENCODER_REGISTRY
from ax.storage.metric_registry import CORE_METRIC_REGISTRY
from ax.storage.runner_registry import CORE_RUNNER_REGISTRY

from boa.wrapper_utils import cd_and_cd_back_dec

logger = logging.getLogger(__name__)


def write_exception_to_log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(
                "Exception encountered in %s. Traceback: %s", func.__name__, traceback.format_exc()
            )

            raise

    return wrapper


class WrapperRegister(ABCMeta):
    def __init__(cls, *args, **kwargs):
        # CORE_ENCODER_REGISTRY[cls] = cls.wrapper_to_dict
        # CORE_DECODER_REGISTRY[cls.__name__] = cls
        cls.write_configs = write_exception_to_log(cd_and_cd_back_dec()(cls.write_configs))
        cls.run_model = write_exception_to_log(cd_and_cd_back_dec()(cls.run_model))
        cls.set_trial_status = write_exception_to_log(cd_and_cd_back_dec()(cls.set_trial_status))
        cls.fetch_trial_data = write_exception_to_log(cd_and_cd_back_dec()(cls.fetch_trial_data))
        super().__init__(*args, **kwargs)


class RunnerRegister(ABCMeta):
    def __init__(cls, *args, **kwargs):
        CORE_ENCODER_REGISTRY[cls] = cls.to_dict
        CORE_DECODER_REGISTRY[cls.__name__] = cls
        next_pk = max(CORE_RUNNER_REGISTRY.values()) + 1
        CORE_RUNNER_REGISTRY[cls] = next_pk


class MetricRegister(ABCMeta):
    def __init__(cls, *args, **kwargs):
        CORE_ENCODER_REGISTRY[cls] = cls.to_dict
        CORE_DECODER_REGISTRY[cls.__name__] = cls
        next_pk = max(CORE_METRIC_REGISTRY.values()) + 1
        CORE_METRIC_REGISTRY[cls] = next_pk


class MetricToEvalRegister(type):
    def __init__(cls, *args, **kwargs):
        CORE_ENCODER_REGISTRY[cls] = cls.to_dict
        CORE_DECODER_REGISTRY[cls.__name__] = cls
