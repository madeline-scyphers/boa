# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

# sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
# sys.path.insert(0, os.path.abspath("../boa/"))
import importlib

import jinja2
import traitlets
from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import ViewList
from sphinx.ext.autodoc import ClassDocumenter
from sphinx.util.nodes import nested_parse_with_titles

from boa.metrics.synthethic_funcs import Hartmann4

# -- Project information -----------------------------------------------------

project = 'boa'
copyright = '2022, Madeline Scyphers, Justine Missik'
author = 'Madeline Scyphers, Justine Missik'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinxext.remoteliteralinclude',
    'myst_nb',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

source_suffix = {
    '.rst': 'restructuredtext',
    '.ipynb': 'myst-nb',
    '.md': 'myst-nb',
    '.myst': 'myst-nb',
}



# torch.nn has doc string reference sphinx has troubles resolving in its own code
# Which get reference when we import from pytorch in general


# Use saved output in notebooks rather than executing on build
# Since the current examples are not part of boa, they need to execute locally
nb_execution_mode = "off"

html_js_files = ["https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.4/require.min.js"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'references']

# -- Autosummary -------------------------------------------------------------
autosummary_generate = True  # Turn on sphinx.ext.autosummary
autoclass_content = "both"  # Add __init__ doc (ie. params) to class summaries
# autosummary_imported_members = True
# html_show_sourcelink = False  # Remove 'view source code' from top of page (for html, not python)
autodoc_inherit_docstrings = True  # If no docstring, inherit from base class
autodoc_member_order = 'bysource'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'pydata_sphinx_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

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
        }]
}


# For to-do extension
todo_include_todos = True


# external project mapping for intersphinx
intersphinx_mapping = {
    'fetch3': ('https://fetch3-nhl.readthedocs.io/en/latest', None),
    'python': ('http://docs.python.org/3', None),
    'numpy': ('http://docs.scipy.org/doc/numpy', None),
    'scipy': ('http://docs.scipy.org/doc/scipy/reference', None),
    'sklearn': ('http://scikit-learn.org/stable', None),
}
# intersphinx_mapping = {
#     # "pytorch": ("https://pytorch.org/docs/stable/", None),
#     "botorch": ("https://botorch.org/api/", None),
#     "ax": ("https://ax.dev/versions/latest/api/", None)
# }
#
#
# class ExcludeClassDocumenter(ClassDocumenter):
#
#     directivetype = 'excluded-class'
#     objtype = 'excludedclass'
#     excluded_classes = [
#         Hartmann4
#     ]
#
#     @classmethod
#     def can_document_member(cls, member, membername, isattr, parent):
#         can_document = isinstance(member, type) and issubclass(member, Hartmann4)
#         if can_document:
#             print("\n\n\n\n\n", can_document)
#             print(member)
#         return can_document
#
#
# EXCLUDE_INHERITED_CLASS = jinja2.Template(
# u"""
# .. autoclass:: {{ classname }}
#    :members:
#    :undoc-members:
# """)
#
#
# def _import_obj(args):
#     """Utility to import the object given arguments to directive"""
#     if len(args) == 1:
#         mod, clsname = args[0].rsplit('.', 1)
#     elif len(args) > 1 and args[-2] == ':module:':
#         mod = args[-1]
#         clsname = args[0].split('(')[0]
#     else:
#         raise ValueError("Args do not look as expected: {0}".format(args))
#     mod = importlib.import_module(mod)
#     return getattr(mod, clsname)
#
#
# class ExcludeClassDirective(Directive):
#     has_content = True
#     required_arguments = 1
#     optional_arguments = 20
#
#     def run(self):
#
#         print("\n\n\n\n\n\nrunning, class: ", self.arguments[0])
#
#         # generate the documentation string
#         rst_text = EXCLUDE_INHERITED_CLASS.render(
#             classname=self.arguments[0]
#         )
#
#
#
#
#         # parse and return documentation
#         result = ViewList()
#         for line in rst_text.split("\n"):
#             result.append(line, "<excluded-class>")
#         node = nodes.paragraph()
#         node.document = self.state.document
#         nested_parse_with_titles(self.state, result, node)
#
#
#         return node.children
#
#
# def setup(app):
#     app.add_autodocumenter(ExcludeClassDocumenter)
#     app.add_directive_to_domain('py', 'excluded-class', ExcludeClassDirective)
