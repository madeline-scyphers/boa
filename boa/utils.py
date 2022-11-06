"""
###################################
General Package Utility Functions
###################################

Utility functions useful for various package things like
getting the signature matching

"""

from __future__ import annotations

import inspect
from collections.abc import Iterable, Mapping
from typing import Any, Callable, Optional, Type


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
