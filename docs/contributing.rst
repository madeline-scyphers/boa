.. _contributions:

###################
Contributing to boa
###################

First make sure you have read :doc:`/user_guide/getting_started` to get your development environment set up

When in question about rst, see references under docs/references in the source code.

Setup pre-commit
---------------------------------------------
We use pre-commit to automatically manage linting on every commit. To set it up, run in your boa development environment::

    pre-commit install

This should now run all of our linting (the same as `invoke style` below) on every commit so you don't accidentally commit code that will fail the CI only because of linting.

Format the code and lint it (check the style)
---------------------------------------------

Run ``invoke style`` to format the code and lint it.

Test your changes
---------------------------------------------

Run ``invoke pytest`` to run the tests.

Ensure your tests past, and add tests for the new code you add.

Build the docs locally
---------------------------------------------

Run ``invoke docs`` to test building the docs.

Ensure your new changes are documented.

Commit your changes
---------------------------------------------

Example::

    git commit -m fix(package): update setup.py arguments 🎉

(emojis are fine too)

or a longer commit message::

    git commit

    package: fix things with stuff

    More commit message things
    and more


You can temporarily bypass pre-commit (The CI jobs on github will still run) if you have something you are in the middle of by add `--no-verify` to your git command::

    git commit --no-verify ...

Push your changes to your fork
---------------------------------------------

Run ``git push origin my_contribution``

Submit a pull request
---------------------------------------------

On github interface, click on ``Pull Request`` button.

Wait for CI to run and one of the developers will review your PR.