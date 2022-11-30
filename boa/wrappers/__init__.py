"""
########################
Creating model wrappers
########################

To create a model wrapper, you will create a child class of boa's :class:`.BaseWrapper`
class. :class:`.BaseWrapper` defines the core functions that must be defined in your model
wrapper:

* :meth:`.BaseWrapper.load_config`: Defines how to load the configuration file for the experiment. There is
  a default version of this function that can be used.
* :meth:`.BaseWrapper.write_configs`: Defines how to write configurations for the model. This is needed so
  that :doc:`BOA </index>` can pass the parameters it generates in each trial to the model.
* :meth:`.BaseWrapper.run_model`: Defines how to run the model.
* :meth:`.BaseWrapper.set_trial_status`: Defines how to determine the status of a trial (i.e., if the model
  run is completed, still running, failed, etc).
* :meth:`.BaseWrapper.fetch_trial_data_single`: Retrieves the trial data (i.e., model outputs) and prepares it for
  the metric(s) used in the objective function.

Apart from these core functions, your model wrapper can have additional functions as needed (for example, to help with
formatting or scaling model outputs)

See :doc:`FETCH3 <fetch3:user_guide/optimization>`'s
:mod:`Wrapper <fetch3:fetch3.optimize.fetch_wrapper>` for an example.


*************************
Example wrapper functions
*************************

The :meth:`.BaseWrapper.write_configs` function
====================================================================

This function is used to write out the configuration files used in an individual optimization trial run,
(i.e. your model's configuration files) or to dynamically write a run script to start an optimization trial run.

This function is how boa gives a new set of parameters for your model to run during each trial.

FETCH3's wrapper provides a simple example of this function for a case where the model's parameters simply need to
be written to a yaml file:

.. rli:: https://raw.githubusercontent.com/jemissik/fetch3_nhl/develop/fetch3/optimize/fetch_wrapper.py
   :pyobject: write_configs

The palm_wrapper used to wrap PALM provides an example of a model with more complicated configuration requirements.
Here, the parameters are written to a YAML file, but then a batch job script must also be written for each
optimization trial run.

.. rli:: https://raw.githubusercontent.com/madeline-scyphers/palm_wrapper/main/palm_wrapper/optimize/wrapper.py
   :pyobject: Wrapper.write_configs


The :meth:`.BaseWrapper.run_model` function
===============================================================

This function defines how to start a run of your model. In most cases,
it can be as simple as launching a python or shell script to start a model run.

FETCH3's wrapper provides an example of
this function for the case where the model run is started by running a python script with command line arguments:

.. rli:: https://raw.githubusercontent.com/jemissik/fetch3_nhl/develop/fetch3/optimize/fetch_wrapper.py
   :pyobject: Fetch3Wrapper.run_model

The palm_wrapper used to wrap PALM takes the batch job script written in ``write_configs`` and runs it, starting a
job on an HPC.
The job script also utilizes the YAML file written above as well.

.. rli:: https://raw.githubusercontent.com/madeline-scyphers/palm_wrapper/main/palm_wrapper/optimize/wrapper.py
   :pyobject: Wrapper.run_model


The :meth:`.BaseWrapper.set_trial_status` function
======================================================================

Marks the status of a trial to reflect the status of the model run associated with that trial.

This function defines the criteria for determining the status of the model run for a trial (e.g., whether
the model run is completed/still running, failed, etc). Each trial will be polled periodically to determine
its status.

The approach for determining the trial status will depend on the structure of the particular model and its
outputs. One way to do this is checking the log files of the model.

In these two examples, the trial status is determined by checking the log file of the model for specific outputs:

.. rli:: https://raw.githubusercontent.com/jemissik/fetch3_nhl/develop/fetch3/optimize/fetch_wrapper.py
   :pyobject: Fetch3Wrapper.set_trial_status

.. rli:: https://raw.githubusercontent.com/madeline-scyphers/palm_wrapper/main/palm_wrapper/optimize/wrapper.py
   :pyobject: Wrapper.set_trial_status

The :meth:`.BaseWrapper.fetch_trial_data_single` function
======================================================================

Retrieves the trial data (i.e., model outputs) and prepares it for the metric(s) used in the objective
function. The return value needs to be a dictionary with the keys matching the keys
of the metric function used in the objective function.

.. rli:: https://raw.githubusercontent.com/jemissik/fetch3_nhl/develop/fetch3/optimize/fetch_wrapper.py
   :pyobject: Fetch3Wrapper.fetch_trial_data


.. rli:: https://raw.githubusercontent.com/madeline-scyphers/palm_wrapper/main/palm_wrapper/optimize/wrapper.py
   :pyobject: Wrapper.fetch_trial_data


Full Examples
==============

.. rli:: https://raw.githubusercontent.com/jemissik/fetch3_nhl/develop/fetch3/optimize/fetch_wrapper.py
   :pyobject: Fetch3Wrapper

link to source: https://github.com/jemissik/fetch3_nhl/blob/develop/fetch3/optimize/fetch_wrapper.py


.. rli:: https://raw.githubusercontent.com/madeline-scyphers/palm_wrapper/main/palm_wrapper/optimize/wrapper.py
   :pyobject: Wrapper

link to source: https://github.com/madeline-scyphers/palm_wrapper/blob/main/palm_wrapper/optimize/wrapper.py

.. toctree::

    /api/boa.wrappers.base_wrapper
    /api/boa.wrappers.wrapper_utils

"""
