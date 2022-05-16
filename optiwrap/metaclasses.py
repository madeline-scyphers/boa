from abc import ABCMeta
from unittest.mock import MagicMock

from ax.storage.json_store.registry import CORE_DECODER_REGISTRY, CORE_ENCODER_REGISTRY
from ax.storage.metric_registry import CORE_METRIC_REGISTRY
from ax.storage.runner_registry import CORE_RUNNER_REGISTRY
from ax.storage.json_store.encoders import runner_to_dict

from optiwrap.wrapper_utils import cd_and_cd_back_dec


class WrapperRegister(ABCMeta):
    def __init__(cls, *args, **kwargs):
        # CORE_ENCODER_REGISTRY[cls] = cls.wrapper_to_dict
        # CORE_DECODER_REGISTRY[cls.__name__] = cls
        cls.write_configs = cd_and_cd_back_dec(cls.write_configs)
        cls.run_model = cd_and_cd_back_dec(cls.run_model)
        cls.set_trial_status = cd_and_cd_back_dec(cls.set_trial_status)
        cls.fetch_trial_data = cd_and_cd_back_dec(cls.fetch_trial_data)
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
        CORE_ENCODER_REGISTRY[cls] = cls.register_cls
        CORE_DECODER_REGISTRY[cls.__name__] = cls
