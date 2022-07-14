"""Module of Invoke tasks regarding CODE QUALITY to be invoked from the command line. Try
invoke --list
from the command line for a list of all available commands.
"""
import os
import shutil

from invoke import task

POSIX = os.name == "posix"


@task
def black(command, checkonly=False):
    """Runs black (autoformatter) on all .py files recursively"""
    print(
        """
Running Black the Python code formatter
=======================================
"""
    )
    cmd = "black --check --diff ." if checkonly else "black ."
    command.run(cmd, echo=True, pty=POSIX)


@task
def isort(command, checkonly=False):
    """Runs isort (import sorter) on all .py files recursively"""
    print(
        """
Running isort the Python code import sorter
===========================================
"""
    )
    cmd = "isort --check-only --diff ." if checkonly else "isort ."
    command.run(cmd, echo=True, pty=POSIX)


@task
def lint(
    command,
):
    """Runs flake8 plugin flakeheaven (linter) on all .py files recursively"""
    print(
        """
Running flakeheaven, a Python code linter
===================================
"""
    )
    command.run("flakeheaven lint", echo=True, pty=POSIX)


@task(pre=[black, isort, lint])
def style(
    command,
):
    """Runs black, isort, and flake8
    Arguments:
        command {[type]} -- [description]
    """
    # If we get to this point all tests listed in 'pre' have  passed
    # unless we have run the task with the --warn flag
    if not command.config.run.warn:
        print(
            """
All Style Checks Passed Successfully
====================================
"""
        )


@task
def test(command, options=""):
    """Runs pytest to identify failing tests and doctests"""

    print(
        """
Running pytest the test framework
=================================
"""
    )
    command.run(f"python -m pytest {options} .", echo=True, pty=POSIX)


@task
def docs(
    command,
):
    """Runs Sphinx to build the docs locally for testing"""
    print(
        """
Running Sphinx to test the docs building
========================================
"""
    )
    shutil.rmtree("docs/_build", ignore_errors=True)
    shutil.rmtree("docs/api", ignore_errors=True)
    shutil.rmtree("docs/jupyter_execute", ignore_errors=True)
    command.run("sphinx-build -b html docs docs/_build", echo=True, pty=POSIX)


@task(pre=[black, isort, lint, test, docs])
def all(
    command,
):
    """Runs black, isort, flake8, and pytest
    Arguments:
        command {[type]} -- [description]
    """
    # If we get to this point all tests listed in 'pre' have passed
    # unless we have run the task with the --warn flag
    if not command.config.run.warn:
        print(
            """
All Style Checks Tests Passed Successfully
==========================================
"""
        )
