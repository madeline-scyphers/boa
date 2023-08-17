"""

###################
Configuration Guide
###################

***********************
Example Configurations
***********************

This configuration can be generated from BOA with the following command::

    python -m boa.config --output-path [path to output]

Default Configuration
==============================

.. literalinclude:: ../../docs/examples/default_config.yaml
    :language: YAML

"""
from boa.config.config import *  # noqa: F401, F403

__all__ = [  # noqa: F405
    "BOAConfig",
    "BOAObjective",
    "BOAScriptOptions",
    "BOAMetric",
    "MetricType",
    # "SchedulerOptions",
    # "GenerationStep",
]
