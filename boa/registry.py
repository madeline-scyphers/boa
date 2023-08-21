import attrs
from ax.storage.json_store.registry import CORE_DECODER_REGISTRY, CORE_ENCODER_REGISTRY


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

    for cls in [BOAObjective, BOAMetric, BOAScriptOptions, BOAConfig]:
        CORE_ENCODER_REGISTRY[cls] = attrs_to_dict
        CORE_DECODER_REGISTRY[cls.__name__] = cls

    # CORE_ENCODER_REGISTRY[MetricType] = str(MetricType)
    CORE_DECODER_REGISTRY[MetricType.__name__] = MetricType
