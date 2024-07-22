from __future__ import annotations

from typing import Type

import botorch.acquisition
import gpytorch.kernels
from ax.storage.botorch_modular_registry import (
    ACQUISITION_FUNCTION_REGISTRY,
    CLASS_TO_REGISTRY,
    CLASS_TO_REVERSE_REGISTRY,
)
from ax.storage.json_store.registry import (
    CORE_CLASS_DECODER_REGISTRY,
    CORE_CLASS_ENCODER_REGISTRY,
    CORE_DECODER_REGISTRY,
    CORE_ENCODER_REGISTRY,
    botorch_modular_to_dict,
    class_from_json,
)


def config_to_dict(inst):
    """Convert Ax runner to a dictionary."""
    d = {k: v for k, v in inst.orig_config.items()}
    return d


def _add_common_encodes_and_decodes():
    """Add common encodes and decodes all at once when function is ran"""

    from boa.config import BOAConfig, MetricType

    CORE_ENCODER_REGISTRY[BOAConfig] = config_to_dict
    # CORE_DECODER_REGISTRY[BOAConfig.__name__] = BOAConfig
    CORE_DECODER_REGISTRY[MetricType.__name__] = MetricType

    CORE_CLASS_DECODER_REGISTRY["Type[Kernel]"] = class_from_json
    CORE_CLASS_ENCODER_REGISTRY[gpytorch.kernels.Kernel] = botorch_modular_to_dict

    KERNEL_REGISTRY = {getattr(gpytorch.kernels, kernel): kernel for kernel in gpytorch.kernels.__all__}

    REVERSE_KERNEL_REGISTRY: dict[str, Type[gpytorch.kernels.Kernel]] = {v: k for k, v in KERNEL_REGISTRY.items()}

    CLASS_TO_REGISTRY[gpytorch.kernels.Kernel] = KERNEL_REGISTRY
    CLASS_TO_REVERSE_REGISTRY[gpytorch.kernels.Kernel] = REVERSE_KERNEL_REGISTRY

    for acq_func_name in botorch.acquisition.__all__:
        acq_func = getattr(botorch.acquisition, acq_func_name)
        if acq_func not in ACQUISITION_FUNCTION_REGISTRY:
            ACQUISITION_FUNCTION_REGISTRY[acq_func] = acq_func_name

    REVERSE_ACQUISITION_FUNCTION_REGISTRY: dict[str, Type[botorch.acquisition.AcquisitionFunction]] = {
        v: k for k, v in ACQUISITION_FUNCTION_REGISTRY.items()
    }

    CLASS_TO_REGISTRY[botorch.acquisition.AcquisitionFunction] = ACQUISITION_FUNCTION_REGISTRY
    CLASS_TO_REVERSE_REGISTRY[botorch.acquisition.AcquisitionFunction] = REVERSE_ACQUISITION_FUNCTION_REGISTRY
