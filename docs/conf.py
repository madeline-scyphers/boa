# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("../boa/"))


from boa._doc_utils import add_ref_to_all_submodules_inits

# -- Project information -----------------------------------------------------

project = "BOA"
copyright = "2022, Madeline Scyphers, Justine Missik"
author = "Madeline Scyphers, Justine Missik"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinxext.remoteliteralinclude",
    "myst_nb",
]

suppress_warnings = ["mystnb.unknown_mime_type"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

source_suffix = {
    ".rst": "restructuredtext",
    ".ipynb": "myst-nb",
    ".md": "myst-nb",
    ".myst": "myst-nb",
}

nitpicky = True
nitpick_ignore = [
    ("py:class", "SearchSpace"),
    ("py:class", "Objective"),
    ("py:class", "BaseTrial"),
    ("py:class", "DBSettings"),
    # ("py:class", "PathLike"),  # TODO, why can't we use type aliases?
]

nitpick_ignore_regex = [
    (r".*", r".*ax.*"),
    (r".*", r".*botorch.*"),
    (r".*", r"array.*like"),
    ("py:class", ".*PathLike"),  # TODO, why can't we use type aliases?
]


nb_execution_mode = "force"

nb_kernel_rgx_aliases = {".*conda.*": "python3"}
nb_execution_excludepatterns = [
    "example_optimization_results.ipynb",
    # "1moo_optimization_run.ipynb",
    # "1optimization_run.ipynb",
    # "1run_r_streamlined.ipynb",
    # "2load_scheduler.ipynb",
    # "2load_moo_scheduler.ipynb",
    # "2EDA_from_r_run.ipynb"
]
nb_execution_timeout = 600
nb_execution_raise_on_error = True
nb_execution_show_tb = True
nb_number_source_lines = True
nb_render_markdown_format = "myst"

html_js_files = ["https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.4/require.min.js"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "references"]

# -- Autosummary -------------------------------------------------------------
autosummary_generate = True  # Turn on sphinx.ext.autosummary
autoclass_content = "both"  # Add __init__ doc (ie. params) to class summaries
# autosummary_imported_members = True
# html_show_sourcelink = False  # Remove "view source code" from top of page (for html, not python)
autodoc_inherit_docstrings = True  # If no docstring, inherit from base class
autodoc_member_order = "bysource"
autodoc_typehints = "both"

# autodoc_type_aliases = {
#     "PathLike": "boa.definitions.PathLike",
#     "SchedulersOrPathList": "boa.plotting.SchedulersOrPathList",
# }
# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "pydata_sphinx_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

html_theme_options = {
    "icon_links": [
        {
            # Label for this link
            "name": "GitHub",
            # URL where the link will redirect
            "url": "https://github.com/madeline-scyphers/boa",  # required
            # Icon class (if "type": "fontawesome"), or path to local image (if "type": "local")
            "icon": "fab fa-github-square",
            # Whether icon should be a FontAwesome class, or a local file
        }
    ]
}


# For to-do extension
todo_include_todos = True

# external project mapping for intersphinx
intersphinx_mapping = {
    "fetch3": ("https://fetch3-nhl.readthedocs.io/en/latest", None),
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "scipy": ("https://docs.scipy.org/doc/scipy", None),
    "sklearn": ("https://scikit-learn.org/stable", None),
    "torch": ("https://pytorch.org/docs/stable", None),
    "panel": ("https://panel.holoviz.org", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
}

# BOA things

# add a reference to the relative __init__.py of all files __doc__ in a submodules
add_ref_to_all_submodules_inits()
