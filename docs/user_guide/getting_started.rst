.. _getting_started:

##############################
Installing and Test Run
##############################

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

If you don't already have a dedicated conda environment for your model::

     conda create -n boa
     conda activate boa

If you don't need to create a new environment, activate the existing conda environment you will be using.

If you are not on an x86 mac (or a mac with python running through rosetta), run these commands to install the dependencies::

    conda install botorch torchvision "sqlalchemy<2.0" "ax-platform==0.2.9" -c pytorch -c gpytorch -c conda-forge

x86 macs (or a mac with python running through rosetta), run::

    conda install pytorch<1.12.0 -c pytorch
    conda install botorch -c pytorch -c gpytorch -c conda-forge
    pip install ax-platform "sqlalchemy<2.0"

Install boa::

    pip install git+https://github.com/madeline-scyphers/boa.git

If you want to install the latest (bleeding-edge) develop version of boa::

    pip install git+https://github.com/madeline-scyphers/boa.git@develop

********************************
Installing for Contributing
********************************

fork the boa repository from `boa's GitHub page <https://github.com/madeline-scyphers/boa>`_.
and then clone your forked repo

From the root directory of the cloned repository, run::

     conda env create
     # If you want to install the dev requirements for development, run this line
     conda env update --name boa --file environment_dev_update.yml

This will install boa in editable mode.

If you plan on running any of the tests in other languages, run::

    conda env update --name boa -f environment_language_updates.yml


mac x86 or apple silicone macs on rosetta python need pytorch>2.0
so if on either of those, it should install pytorch>2 by default
but if not and something doesn't work, upgrade pytorch, torchvision,
and torchaudio

********
Test run
********

Once everything is installed, run the test script to ensure everything is install properly::

    python -m boa.scripts.run_branin

If this test case runs successfully, you can move on to the next steps.

:doc:`/contributing`

If you have errors, see the :doc:`/troubleshooting` section.
