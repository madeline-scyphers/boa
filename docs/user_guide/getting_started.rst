.. _getting_started:
###############
Getting Started
###############

************
Installation
************

Install Python
==============

To use ``boa``, you must first have Python and the conda package manager
installed. There are two options for this:

- **Install Anaconda**: This is the recommended option for those who are new to
  Python. Anaconda comes with a few choices of IDEs and Jupyter Notebook, which can be used to run interactive Python
  notebooks such as those in boa's examples. To install Anaconda, see
  `directions for installing Anaconda <https://docs.anaconda.com/anaconda/install/index.html>`_.
- **Install Miniconda**: If you want a more minimal installation without any extra
  packages, would prefer to handle installing a Python IDE yourself, and would prefer
  to work from the command line instead of using the graphical interface provided
  by Anaconda Navigator, you might prefer to install Miniconda rather than Anaconda.
  Miniconda is a minimal version of Anaconda that includes just conda, its dependencies,
  and Python. To install Miniconda, see
  `directions for installing Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_.

Install boa
===========

If you need to create a new environment:

     conda create -n boa
     conda activate boa

If you don't need to create a new environment, activate that environment
Then install dependencies

    conda install botorch -c pytorch -c gpytorch -c conda-forge
    pip install ax-platform

Install BOA
    pip install git+https://github.com/madeline-scyphers/boa.git

Install the develop version of BOA
    pip install git+https://github.com/madeline-scyphers/boa.git@develop

********************************
Installing for Contributing
********************************

Clone the boa repository from `boa's GitHub page <https://github.com/madeline-scyphers/boa>`_.

If you are not on an x86 mac (or a mac with python running through rosetta), from the root directory of the cloned repository, run::

     conda env create
     # If you want to install the dev requirements for development, run this line
     conda env update --name boa --file environment_dev_update.yml

x86 macs (or a mac with python running through rosetta), run::

     conda env create --file environment_mac_x86.yml
     # If you want to install the dev requirements for development, run this line
     conda env update --name boa --file environment_dev_update.yml

This will install boa in editable mode.

********
Test run
********

Once everything is installed, run the test script to ensure everything is install properly::

    python -m boa.test_scripts.run_branin

If this test case runs successfully, you can move on to the next steps.

:ref:`contributions`

If you have errors, see the :ref:`Troubleshooting` section.
