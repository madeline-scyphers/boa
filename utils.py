from __future__ import annotations

import inspect
from typing import Callable


def get_callable_signature(callable: Callable) -> inspect.Signature:
    return inspect.signature(callable)


def get_dictionary_matching_signature(signature: inspect.Signature, d: dict) -> dict:
    params = signature.parameters
    return {k: v for k, v in d.items() if k in params}

def get_dictionary_from_callable(callable: Callable, d: dict) -> dict:
    signature = get_callable_signature(callable)
    return get_dictionary_matching_signature(signature, d)