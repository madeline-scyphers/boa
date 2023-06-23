"""
###################################
General Package Utility Functions
###################################

Utility functions useful for various package things like
getting the signature matching

"""

from __future__ import annotations

import importlib
import inspect
import sys
import types
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Callable, Optional, Type

import torch

from boa.definitions import PathLike

# Maybe at some point we can do a thing that allows you to import from a note book
# But not right now
#
# def find_notebook(fullname, path=None):
#     """find a notebook, given its fully qualified name and an optional path
#
#     This turns "foo.bar" into "foo/bar.ipynb"
#     and tries turning "Foo_Bar" into "Foo Bar" if Foo_Bar
#     does not exist.
#     """
#     name = fullname.rsplit('.', 1)[-1]
#     if not path:
#         path = ['']
#     for d in path:
#         nb_path = os.path.join(d, name + ".ipynb")
#         if os.path.isfile(nb_path):
#             return nb_path
#         # let import Notebook_Name find "Notebook Name.ipynb"
#         nb_path = nb_path.replace("_", " ")
#         if os.path.isfile(nb_path):
#             return nb_path
#
#
# class NotebookLoader(object):
#     """Module Loader for Jupyter Notebooks"""
#     def __init__(self, path=None):
#         from IPython.core.interactiveshell import InteractiveShell
#         self.shell = InteractiveShell.instance()
#         self.path = path
#
#     def load_module(self, fullname):
#         import io
#         import types
#         from IPython import get_ipython
#         from nbformat import read
#         import sys
#         """import a notebook as a module"""
#         path = find_notebook(fullname, self.path)
#
#         print ("importing Jupyter notebook from %s" % path)
#
#         # load the notebook object
#         with io.open(path, 'r', encoding='utf-8') as f:
#             nb = read(f, 4)
#
#
#         # create the module and add it to sys.modules
#         # if name in sys.modules:
#         #    return sys.modules[name]
#         mod = types.ModuleType(fullname)
#         mod.__file__ = path
#         mod.__loader__ = self
#         mod.__dict__['get_ipython'] = get_ipython
#         sys.modules[fullname] = mod
#
#         # extra work to ensure that magics that would affect the user_ns
#         # actually affect the notebook module's ns
#         save_user_ns = self.shell.user_ns
#         self.shell.user_ns = mod.__dict__
#
#         try:
#           for cell in nb.cells:
#             if cell.cell_type == 'code':
#                 # transform the input to executable Python
#                 code = self.shell.input_transformer_manager.transform_cell(cell.source)
#                 # run the code in themodule
#                 exec(code, mod.__dict__)
#         finally:
#             self.shell.user_ns = save_user_ns
#         return mod
#
#
# class NotebookFinder(object):
#     """Module finder that locates Jupyter Notebooks"""
#     def __init__(self):
#         self.loaders = {}
#
#     def find_module(self, fullname, path=None):
#         nb_path = find_notebook(fullname, path)
#         if not nb_path:
#             return
#
#         key = path
#         if path:
#             # lists aren't hashable
#             key = os.path.sep.join(path)
#
#         if key not in self.loaders:
#             self.loaders[key] = NotebookLoader(path)
#         return self.loaders[key]
#
# sys.meta_path.append(NotebookFinder())


def get_callable_signature(callable: Callable) -> inspect.Signature:
    return inspect.signature(callable)


def get_dictionary_matching_signature(
    signature: inspect.Signature,
    d: dict,
    match_private: bool = False,
    exclude_fields: Optional[list[str]] = None,
    accept_all_kwargs: bool = True,
) -> dict:
    args = {}
    exclude_fields = exclude_fields or []
    params = signature.parameters

    has_kwargs = inspect.Parameter.VAR_KEYWORD in [param.kind for param in params.values()]
    if accept_all_kwargs and has_kwargs:
        for key, value in d.items():
            if match_private and (key.startswith("_") or key.startswith("__")):
                key = key.lstrip("_")
            if key not in exclude_fields:
                args[key] = value
        return args

    for key, value in d.items():
        if match_private and (key.startswith("_") or key.startswith("__")):
            key = key.lstrip("_")
        if key in params and key not in exclude_fields:
            args[key] = value
    return args


def get_dictionary_from_callable(callable: Callable, d: dict, **kwargs) -> dict:
    signature = get_callable_signature(callable)
    return get_dictionary_matching_signature(signature, d, **kwargs)


def serialize_init_args(class_, *, parents: list[Type] = None, match_private: bool = False, **kwargs):
    """Given an object, return a dictionary of the arguments that are
    needed by its constructor.
    """
    args = vars(class_)  # TODO don't use vars? maybe?
    return extract_init_args(args, class_=class_, parents=parents, match_private=match_private, **kwargs)


def _load_module_from_path(module_path: PathLike, module_name: str = None) -> types.ModuleType:
    """Load a module dynamically from a path"""
    if module_name is None:
        module_name = Path(module_path).name
    sys.path.append(str(Path(module_path).parent))
    # create a module spec from a file location, so we can then load that module
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None:
        raise ValueError(f"Path to loading module is invalid. Check path to module{module_path}")
    # create that module from that spec from above
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    # execute the loading and importing of the module
    spec.loader.exec_module(module)

    # return loaded module
    return module


def _load_attr_from_module(module: types.ModuleType, to_load: str) -> Type | Callable | Any:
    try:
        return getattr(module, to_load)
    except AttributeError as e:
        raise AttributeError(
            f"{to_load} was not found in {module}. "
            f"Attributes cannot be loaded from notebooks."
            f"If you are defining modules in notebooks, move them to .py files"
        ) from e


def extract_init_args(
    args: dict[str, Any], class_: Type, *, parents: list[Type] = None, match_private: bool = False, **kwargs
) -> dict[str, Any]:
    """Given a dictionary, extract the arguments required for the
    given class's constructor.
    """
    parents = parents or []
    kw = {}

    parents_init = [parent.__init__ for parent in parents]
    init_ls = [class_.__class__.__init__, *parents_init]
    for init in init_ls:
        kw.update(get_dictionary_from_callable(init, args, match_private=match_private, **kwargs))
    return kw


def torch_device():
    if torch.cuda.is_available():
        device = "cuda"
    # not all torch features are available in mps right now, so we hold off on mps for now
    # elif torch.backends.mps.is_available():
    #     device = "mps"
    else:
        device = "cpu"
    return torch.device(device)


def convert_type(maybe_iterable, conversion: dict, new_dict: dict = None):
    new_dict = new_dict or {}
    if isinstance(maybe_iterable, Iterable) and not isinstance(maybe_iterable, str):
        if isinstance(maybe_iterable, Mapping):
            for key, value in maybe_iterable.items():
                new_dict[_convert_type(key, conversion)] = convert_type(value, conversion, {})
        else:
            for index, item in enumerate(maybe_iterable):
                maybe_iterable[index] = convert_type(item, conversion, new_dict)
            return maybe_iterable
    else:
        return _convert_type(maybe_iterable, conversion)

    return new_dict


def _convert_type(item, conversion: dict):
    for type_ in conversion:
        if isinstance(item, type_):
            if type(item) in conversion:
                return conversion[type(item)](item)  # directly use the item passed in
            return conversion[type_](item)
    return item
