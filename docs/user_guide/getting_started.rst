.. _getting_started:

##############################
Installing and Test Run
##############################

************
Installation
************

Install Python
==============

To use ``boa``, you must first have Python installed, either with conda or other.

Here are instructions on how to install python through Anaconda or miniconda:

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

If using conda and you don't already have a dedicated conda environment for your model (if using mamba, replace all conda calls with mamba)::

     conda create -n boa
     conda activate boa

or if not using Python, make sure you have a virtual environment create::

    python -m venv venv

and activate the virtual environment,
on windows::

    . venv\Scripts\activate.bat

on linux and mac::

    . venv/bin/activate

Once your environment is activated, if using conda, run::

    conda install boa-framework -c pytorch -c conda-forge

If not using conda, run::

    pip install boa-framework

If you want to install the latest (bleeding-edge) develop version of boa::

    pip install git+https://github.com/madeline-scyphers/boa.git@develop

********************************
Installing for Contributing
********************************

fork the boa repository from `boa's GitHub page <https://github.com/madeline-scyphers/boa>`_.
and then clone your forked repo

From the root directory of the cloned repository, run::

     conda env create --file environment_dev.yml

This will install boa in editable mode.

mac x86 or apple silicone macs on rosetta python need pytorch>2.0
so if on either of those, it should install pytorch>2 by default
but if not and something doesn't work, upgrade pytorch, torchvision,
and torchaudio

and then activate this environment::

    conda activate boa-dev

:doc:`/contributing`

********
Test run
********

Once everything is installed, run the test script to ensure everything is install properly::

    boa.scripts.run_branin

If this test case runs successfully, you can move on to the next steps.

If you encounter a problem, make sure you environment that you install boa into is activated (`conda activate boa`, `. venv/bin/activate`, or `. venv\Scripts\activate.bat` for conda or pip (unix or windows), see above)), and then try again. If it still doesn't work, you can try::

    python -m boa.scripts.run_branin

If this works, it may mean it installed an older version of BOA or that the boa command is not found on your path. If this works, you should be able to run boa commands by using the `python -m boa` instead of just `boa` and the plot command with `python -m boa.plot`.

**********
Update BOA
**********

To update BOA

if using Conda to install BOA, run::

    conda update boa-framework

if using pip to install BOA, run::

    pip install -U boa-framework

If you have errors, see the :doc:`/troubleshooting` section.
