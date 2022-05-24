# Run from root directory, not this directory

rm -rf docs/_build
rm -rf docs/api
sphinx-build -b html docs docs/_build