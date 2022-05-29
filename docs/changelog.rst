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
    Bugfixes for the optiwrap code base

Configuration
==============

..
    Changes to how optiwrap can be configured

Depreciation
==============

..
    Changes to optiwrap's code that deprecates previous code or behavior

Documentation
==============

..
    Major changes to documentation and policies. Small docs changes
     don't need a changelog entry.

Feature
==============

..
    New Features added to optiwrap

Packaging
==============

..
    Changes to how optiwrap is packaged, such as dependency requirements

Refactor
==============

..
    Changes to how optiwrap's code with no changes to behavior

Removals
==============

..
    BREAKING changes of code or behavior in optiwrap

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
