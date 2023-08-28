from ax.storage.json_store.registry import CORE_DECODER_REGISTRY, CORE_ENCODER_REGISTRY


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
