"""Module of Invoke tasks regarding CODE QUALITY to be invoked from the command line. Try
invoke --list
from the command line for a list of all available commands.
"""
import os
import shutil

from invoke import task

POSIX = os.name == "posix"
# we test these one at a time, b/c we get a ImportPathMismatchError with doctest and pytest from modules called
# the same thing in different packages (such as a wrapper.py docs and in boa)
TEST_DIRECTORIES = [
    "boa",
    # "docs", we have no doctests in docs yet, so this running returns none, which fails, which isn't what we want
    "tests",
]


@task
def black(command, checkonly=False):
    """Runs black (autoformatter) on all .py files recursively
    if checkonly=True, only checks if would change files
    """
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
    """Runs isort (import sorter) on all .py files recursively
    if checkonly=True, only checks if would change files
    """
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


@task
def style(command, checkonly=False):
    """Runs black, isort, and flake8
    if checkonly=True, only checks if would change files
    """
    black(command, checkonly=checkonly)
    isort(command, checkonly=checkonly)
    lint(command)
    # Only prints if doesn't exit from the above not failing out
    print(
        """
All Style Checks Passed Successfully
====================================
"""
    )


@task
def test_dir(command, options="", dir_="."):
    """Runs pytest to identify failing tests and doctests"""

    print(
        """
Running pytest the test framework
=================================
"""
    )
    command.run(f"python -m pytest {options} {dir_}", echo=True, pty=POSIX)


@task(aliases=["tests"])
def test(command, options=""):
    """Runs pytest to identify failing tests and doctests"""

    print(
        """
Running pytest the test framework
=================================
"""
    )
    for dir_ in TEST_DIRECTORIES:
        test_dir(command, options=options, dir_=dir_)
    # command.run(f"python -m pytest {options} {' '.join(dir_ for dir_ in TEST_DIRECTORIES)}", echo=True, pty=POSIX)

    print(
        """
All Testing Directories Passed Successfully
===========================================
"""
    )


@task
def docs(command, warn_is_error=False):
    """Runs Sphinx to build the docs locally for testing"""
    print(
        """
Running Sphinx to test the docs building
========================================
"""
    )
    options = "-W " if warn_is_error else ""
    shutil.rmtree("docs/_build", ignore_errors=True)
    shutil.rmtree("docs/api", ignore_errors=True)
    shutil.rmtree("docs/code_reference/api", ignore_errors=True)
    shutil.rmtree("docs/jupyter_execute", ignore_errors=True)
    command.run(f"sphinx-build {options}-b html docs docs/_build", echo=True, pty=POSIX)


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
All Checks Passed Successfully
==========================================
"""
        )
