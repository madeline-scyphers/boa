"""
########################
Meta Classes
########################

Meta class modify class behaviors. For example, the :class:`.WrapperRegister` ensures that all subclasses of
:class:`.BaseWrapper` will wrap functions in :func:`.cd_and_cd_back_dec`
to make sure that if users do any directory changes inside a wrapper function,
the original directory is returned to afterwards.

"""
from abc import ABCMeta
from functools import wraps

from ax.storage.json_store.registry import CORE_DECODER_REGISTRY, CORE_ENCODER_REGISTRY
from ax.storage.metric_registry import CORE_METRIC_REGISTRY
from ax.storage.runner_registry import CORE_RUNNER_REGISTRY

from boa.registry import _add_common_encodes_and_decodes
from boa.wrappers.wrapper_utils import cd_and_cd_back_dec
from boa.logger import get_logger

logger = get_logger(__name__)


def write_exception_to_log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Boa Wrapper encountered Exception: {e!r} in %s", func.__name__)
            raise

    return wrapper


class WrapperRegister(ABCMeta):
    def __init__(cls, *args, **kwargs):
        # CORE_ENCODER_REGISTRY[cls] = cls.wrapper_to_dict
        # CORE_DECODER_REGISTRY[cls.__name__] = cls
        _add_common_encodes_and_decodes()
        cls.load_config = write_exception_to_log(cd_and_cd_back_dec()(cls.load_config))
        cls.mk_experiment_dir = write_exception_to_log(cd_and_cd_back_dec()(cls.mk_experiment_dir))
        cls.write_configs = write_exception_to_log(cd_and_cd_back_dec()(cls.write_configs))
        cls.run_model = write_exception_to_log(cd_and_cd_back_dec()(cls.run_model))
        cls.set_trial_status = write_exception_to_log(cd_and_cd_back_dec()(cls.set_trial_status))
        cls.fetch_trial_data_single = write_exception_to_log(cd_and_cd_back_dec()(cls.fetch_trial_data_single))
        cls.fetch_all_trial_data = write_exception_to_log(cd_and_cd_back_dec()(cls.fetch_all_trial_data))
        cls._fetch_all_metrics = write_exception_to_log(cd_and_cd_back_dec()(cls._fetch_all_metrics))
        super().__init__(*args, **kwargs)


class RunnerRegister(ABCMeta):
    def __init__(cls, *args, **kwargs):
        _add_common_encodes_and_decodes()
        CORE_ENCODER_REGISTRY[cls] = cls.to_dict
        CORE_DECODER_REGISTRY[cls.__name__] = cls
        next_pk = max(CORE_RUNNER_REGISTRY.values()) + 1
        CORE_RUNNER_REGISTRY[cls] = next_pk


class MetricRegister(ABCMeta):
    def __init__(cls, *args, **kwargs):
        _add_common_encodes_and_decodes()
        CORE_ENCODER_REGISTRY[cls] = cls.to_dict
        CORE_DECODER_REGISTRY[cls.__name__] = cls
        next_pk = max(CORE_METRIC_REGISTRY.values()) + 1
        CORE_METRIC_REGISTRY[cls] = next_pk
