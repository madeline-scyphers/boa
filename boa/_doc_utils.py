import importlib
import pkgutil

import boa


def get_boa_submodules():
    print(boa)
    module_list = []
    packages = []
    for module_finder, modname, is_pkg in pkgutil.walk_packages(boa.__path__):
        if is_pkg:
            packages.append(modname)
        if len(modname.split(".")) > 1:
            module_list.append(modname)
    return module_list


def import_boa_submod(submod_str):
    return importlib.import_module(f"boa.{submod_str}")


def add_ref_to_all_submodules_inits():
    module_list = get_boa_submodules()
    for mod_str in module_list:
        submod = import_boa_submod(mod_str)
        info = f"""**Overview Information Here**: :mod:`{submod.__package__}`"""

        submod.__doc__ = f"{submod.__doc__}\n\n{info}" if submod.__doc__ else info
