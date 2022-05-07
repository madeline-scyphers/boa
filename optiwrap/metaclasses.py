from abc import ABCMeta

from optiwrap.wrapper_utils import cd_and_cd_back_dec
from ax.storage.json_store.registry import CORE_DECODER_REGISTRY, CORE_ENCODER_REGISTRY
from ax.storage.json_store.encoders import runner_to_dict, metric_to_dict


class WrapperRegister(ABCMeta):
    def __init__(cls, *args, **kwargs):
        CORE_ENCODER_REGISTRY[cls] = cls.wrapper_to_dict
        CORE_DECODER_REGISTRY[cls.__name__] = cls
        cls.write_configs = cd_and_cd_back_dec(cls.write_configs)
        cls.run_model = cd_and_cd_back_dec(cls.run_model)
        cls.set_trial_status = cd_and_cd_back_dec(cls.set_trial_status)
        cls.fetch_trial_data = cd_and_cd_back_dec(cls.fetch_trial_data)
        super().__init__(*args, **kwargs)


class RunnerRegister(ABCMeta):
    def __init__(cls, *args, **kwargs):
        CORE_ENCODER_REGISTRY[cls] = runner_to_dict
        CORE_DECODER_REGISTRY[cls.__name__] = cls


class MetricRegister(ABCMeta):
    def __init__(cls, *args, **kwargs):
        CORE_ENCODER_REGISTRY[cls] = metric_to_dict
        CORE_DECODER_REGISTRY[cls.__name__] = cls
