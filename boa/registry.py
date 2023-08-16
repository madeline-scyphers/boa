import pathlib

import attrs
from ax.storage.json_store.registry import CORE_DECODER_REGISTRY, CORE_ENCODER_REGISTRY


class _ConstructPathlib:
    """
    Stupid way to hack a function because Ax decoder requires it to be a class
    and only passes keyword arguments only. Pathlib only takes positional arguments,
    so this class converts the encoded dictionary from encode and decodes it as
    positional arguments and returns a Path object (like a function, but hacky)
    """

    def __new__(cls, pathsegments):
        return pathlib.Path(*pathsegments)


def attrs_to_dict(inst):
    """Convert Ax runner to a dictionary."""
    d = attrs.asdict(
        inst,
        filter=lambda attr, value: True
        if not inst._filtered_dict_fields
        else attr.name not in inst._filtered_dict_fields,
    )
    d["__type"] = inst.__class__.__name__
    return d


def _add_common_encodes_and_decodes():
    """Add common encodes and decodes all at once when function is ran"""
    from boa.config import (
        BOAConfig,
        BOAMetric,
        BOAObjective,
        BOAScriptOptions,
        MetricType,
    )
    from boa.wrappers.base_wrapper import BaseWrapper
    from boa.wrappers.script_wrapper import ScriptWrapper

    # for obj in [
    #     pathlib.Path,
    #     pathlib.PurePath,
    #     pathlib.PosixPath,
    #     pathlib.WindowsPath,
    #     pathlib.PurePosixPath,
    #     pathlib.PureWindowsPath,
    # ]:
    #     CORE_ENCODER_REGISTRY[obj] = lambda p: dict(__type=obj.__name__, pathsegments=[str(p)])
    #     CORE_DECODER_REGISTRY[obj.__name__] = _ConstructPathlib

    for cls in [BOAObjective, BOAMetric, BOAScriptOptions, BOAConfig]:
        CORE_ENCODER_REGISTRY[cls] = attrs_to_dict
        CORE_DECODER_REGISTRY[cls.__name__] = cls

    # CORE_ENCODER_REGISTRY[MetricType] = str(MetricType)
    CORE_DECODER_REGISTRY[MetricType.__name__] = MetricType

    CORE_ENCODER_REGISTRY[BaseWrapper] = BaseWrapper.to_dict
    CORE_DECODER_REGISTRY[BaseWrapper.__name__] = BaseWrapper.from_dict
    CORE_ENCODER_REGISTRY[ScriptWrapper] = ScriptWrapper.to_dict
    CORE_DECODER_REGISTRY[ScriptWrapper.__name__] = ScriptWrapper.from_dict
