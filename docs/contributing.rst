.. _contributions:
###################
Contributing to boa
###################

First make sure you have read :ref:`getting_started` to get your development environment set up

When in question about rst, see references under docs/references in the source code.

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

Example: ``fix(package): update setup.py arguments 🎉`` (emojis are fine too)

Push your changes to your fork
---------------------------------------------

Run ``git push origin my_contribution``

Submit a pull request
---------------------------------------------

On github interface, click on ``Pull Request`` button.

Wait for CI to run and one of the developers will review your PR.