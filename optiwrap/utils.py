from __future__ import annotations

import inspect
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
