from __future__ import annotations

import inspect
from collections import Iterable, Mapping
from collections.abc import Iterable, Mapping
from typing import Callable


def get_callable_signature(callable: Callable) -> inspect.Signature:
    return inspect.signature(callable)


def get_dictionary_matching_signature(
    signature: inspect.Signature, d: dict, match_private: bool = False
) -> dict:
    params = signature.parameters
    args = {}
    for key, value in d.items():
        if match_private and (key.startswith("_") or key.startswith("__")):
            key = key.lstrip("_")
        if key in params:
            args[key] = value
    return args


def get_dictionary_from_callable(callable: Callable, d: dict, **kwargs) -> dict:
    signature = get_callable_signature(callable)
    return get_dictionary_matching_signature(signature, d, **kwargs)


def serialize_init_args(instance, *, parents, match_private: bool = False):
    parents = parents or []
    args = vars(instance)  # TODO don't use vars?
    kw = {}

    parents_init = [parent.__init__ for parent in parents]
    callable_ls = [instance.__class__.__init__, *parents_init]
    for callable in callable_ls:
        kw.update(get_dictionary_from_callable(callable, args, match_private=match_private))
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
