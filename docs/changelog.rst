#########
Changelog
#########

************
Unreleased
************

Highlights
==============

..
    Include any especially major or disruptive changes here

Bugfixes
==============

..
    Bugfixes for the boa code base

Configuration
==============

..
    Changes to how boa can be configured

Depreciation
==============

..
    Changes to boa's code that deprecates previous code or behavior

Documentation
==============

..
    Major changes to documentation and policies. Small docs changes
     don't need a changelog entry.

Feature
==============

..
    New Features added to boa

Packaging
==============

..
- Package name changed to boa

Refactor
==============

..
    Changes to how boa's code with no changes to behavior

Removals
==============

..
    BREAKING changes of code or behavior in boa

Development
==============

..
    Changes to development environment, tools, etc.

- CLI
    - Add invoke cli tools to easily run linting, pytest, and other tools. example:

        ``invoke style``

        runs black, isort, and flakeheaven (plugin for flake8)
- CI
    - Add a CI.yaml file for GitHub actions
        - Does linting check on every push and pull request to develop or main to check flakeheaven, black, and isort would pass.
        - Does automated testing on every push and pull request to develop and main.

Other
==============

..
    Things that don't fit into the above categories
