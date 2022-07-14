################
Package Overview
################

.. todo::
   - General description of how boa works
   - Overview of package structure
   - Overview of basic steps for creating a model wrapper
   - Overview of main features

There are 3 core components to running boa, configuration,
a model wrapper, and a run script. Each are detailed below.

*****************************
Creating a configuration File
*****************************

Configuration is usually done through a configuration file in YAML or json format. The goal of boa is allow as much functionality of the bayesian optimization through the configuration as possible. Allowing users to worry mostly about their model itself instead of the optimization. In the configuration file you can do a single objective, multi objective, or scalarize objective optimization. You can specify different acquisition functions, or let them be selected for you, what parameters you are optimizing, parameter constraints, outcome constraints, and more.

See the :ref:`instructions for configurations files<configuration>` for details.

.. note::
    We are adding more and more functionality to the configuration directly, but if there are features not supported in the boa configuration file yet, but are support in the underlying Ax or botorch libraries, you can customize things further  with your run script. See below.


Objective functions
====================

When specifying your objective function to minimize or maximize, boa comes with a number of metrics you can use with your model output, such as MSE, :math:`R^2`, and others. For a list of current list of premade available of metrics, see See :class:`boa.metrics.metrics.METRICS`



************************
Creating a model wrapper
************************

Using a model with boa requires writing a minimal wrapper to define the essential functions needed for boa to interact
with the model (i.e. reading and writing configurations for the model, running the model, and retrieving outputs from
the model).

.. note::
    A goal for the next stage of development is to allow for model wrapper functions to be written in other languages
    (e.g., R)

See the :ref:`instructions for creating a model wrapper <wrapper-user-guide>` for details.

************************
Creating a run script
************************

A basic run script to initialize your wrapper, load your configuration, and run your optimization.

See the :ref:`instructions for creating a run script <run_script>` for details.

.. note::
    A goal for the next stage of development is for standard run scripts not be needed, and boa handle all based on configuration and your wrapper. And you will only need to make a run script if you need more customization.

.. toctree::
    :maxdepth: 2

    wrapper
    configuration
    run_script
