##############
Code reference
##############

Check out the user guide section as well!

.. toctree::
    :maxdepth: 2

    /user_guide/index

:doc:`Wrappers and Tools <api/boa.wrappers>`
=============================================

This is where you will find information about :doc:`BOA's </index>` Wrapper classes for optimization, as well as general wrapping utility functions that might be useful to wrap a model


.. autosummary::
    :toctree: api
    :template: custom_module_template_short.rst

    boa.config
    boa.wrappers
    boa.wrappers.base_wrapper
    boa.wrappers.script_wrapper
    boa.wrappers.wrapper_utils

:doc:`Metrics <api/boa.metrics>`:
=================================

This is where you will find information about :doc:`BOA's </index>` Metrics.

.. autosummary::
    :toctree: api
    :template: custom_module_template_short.rst
    :recursive:

    boa.metrics
    boa.metrics.metrics

Saving and Loading your Experiment
===================================

.. autosummary::
    :toctree: api
    :template: custom_module_template_short.rst

    boa.storage

Plotting your Experiment
===================================

.. autosummary::
    :toctree: api
    :template: custom_module_template_short.rst

    boa.plot
    boa.plotting


Advanced Usage/Direct Python Access
====================================

.. autosummary::
    :toctree: api
    :template: custom_module_template_short.rst

    boa.controller
    boa.scheduler
    boa.ax_instantiation_utils
    boa.runner
    boa.utils
    boa.metaclasses
    boa.instantiation_base
    boa.template
