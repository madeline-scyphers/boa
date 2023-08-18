"""

###################
Configuration Guide
###################


***********************
Example Configurations
***********************


Default Configuration
==============================

.. literalinclude:: ../../docs/examples/default_config.yaml
    :language: YAML


Jinja2 Templating
==============================

BOA supports Jinja2 templating in the configuration file. This allows for
the use of variables and conditionals in the configuration file. For example,
the following configuration file uses Jinja2 templating to set the
``parameters`` and ``parameter_constraints`` fields based on a loop.
Much more complex templating is possible, including the use of conditionals.
See :std:doc:`Jinja2 <jinja2:intro>` for more information on Jinja2 templating
and additional options and examples.

.. literalinclude:: ../../tests/test_configs/test_config_jinja2.yaml

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
