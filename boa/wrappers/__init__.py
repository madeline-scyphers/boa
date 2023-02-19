"""
########################
Creating model wrappers
########################

---------------------------
Language Agnostic Interface
---------------------------

The language agnostic interface revolves around you writing 1 or more script(s) (detailed below)
and :doc:`BOA </index>` passing a command line argument to this 1 or more script(s) which
is the path to a folder with json files that contain optimization information, such as the
parameters for a trial.

You have a few options on the number of scripts to write. The options are listed below:

* Write Configs: this script is supposed to let you write out any configurations or setup stuff
  your model may need to run. It is called right before the `Run Model Script` to let you do
  set up stuff.
  (This script is optional, and much or all of this can be accomplished in your
  Run Model script, but is provided to allow code partitioning options)
* Run Model: This is the script that actually runs your model codel. This can be directly in
  this script, or maybe this script kicks off another script that is your model. For example
  maybe this script is your model script, but maybe you write a convenience wrapper in R to
  interface with a Fortran model, this could kick off your R interface code.
* Set Trial Status: This script writes out to BOA if your trial passed or failed.
  (This script is optional, and much or all of this can be accomplished in your
  `Run Model Script` or your `Fetch Trial Data Script`, but is provided to allow code
  partitioning options)
* Fetch Trial Data: This script writes out your data for BOA to consume.
  (This script is optional, and much or all of this can be accomplished in your
  `Run Model Script`, but is provided to allow code partitioning options)

To run any of these scripts, in your config file, you will add command line run commands
(as in what you would type in your terminal (bash, zsh, powershell, windows command prompt, etc.)
to start your script. This might be something like `Rscript run_model.R` or `python run_model.py`).
Keep in mind that BOA will run this command directly, so if you use relative paths (such as in
the example in the previous sentence), then the working directory by default will be the directory
that your config file is in. To add these run commands to your configuration file, add them
to the following sections

..  code-block:: YAML

    script_options:
        write_configs: whatever your write_configs run command is  # only include if you are using a `Write Configs Script`
        run_model: whatever your run_model run command is
        set_trial_status: whatever your set_trial_status run command is  # only include if you are using a `Set Trial Status Script`
        fetch_trial_data: whatever your fetch_trial_data run command is  # only include if you are using a `Fetch Trial Data Script`

Here is an example of a `Run Model Script` that handles setting the trial status and outputting
the data back to BOA as well. So this script is all that is needed (other than the model itself,
which in this case is a synthetic function called hartman6, but that is just a stand in for any
black box model call).

.. literalinclude:: ../../tests/scripts/other_langs/r_package_streamlined/run_model.R
    :language: R

-------------------------
Python Interface
-------------------------

To create a model wrapper, you will create a child class of :doc:`BOA </index>`'s :class:`.BaseWrapper`
class. :class:`.BaseWrapper` defines the core functions that must be defined in your model
wrapper:

* :meth:`.BaseWrapper.load_config`: Defines how to load the configuration file for the experiment. There is
  a default version of this function that can be used.
* :meth:`.BaseWrapper.write_configs`: Defines how to write configurations for the model. This is needed so
  that :doc:`BOA </index>` can pass the parameters it generates in each trial to the model.
* :meth:`.BaseWrapper.run_model`: Defines how to run the model.
* :meth:`.BaseWrapper.set_trial_status`: Defines how to determine the status of a trial (i.e., if the model
  run is completed, still running, failed, etc).
* :meth:`.BaseWrapper.fetch_trial_data`: Retrieves the trial data (i.e., model outputs) and prepares it for
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

The :meth:`.BaseWrapper.fetch_trial_data` function
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
