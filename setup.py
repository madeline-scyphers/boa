from pathlib import Path

from setuptools import setup

BASE_ENV = Path(__file__).resolve().parent / "environment.yml"
DEV_ENV = Path(__file__).resolve().parent / "environment_dev.yml"


# dictionary of any package renaming from conda package names to PyPI names
# ex) PyTorch is pytorch on conda, but listed as torch on PyPI
# also if you are installing a pkg from a git rep, you should remap it
# to "git+https/etc": "pkg_name @ git+https/etc"
pkg_renames = {"pytorch": "torch"}


# list of any packages in your environment files you don't want to include
# They have to be the exact text of the pkg name, including any version info
# (example, numpy<=42)
# You should also not include any packages that aren't python packages
# such as nodejs, git, GDAL, etc.
pkgs_to_exclude = []


def remove_non_pkgs(pkg: str):
    is_pip = "-pip" in pkg
    is_python = "-python=" in pkg
    is_self = "--e." in pkg
    is_inline_cmt = pkg.startswith("#")
    if not is_pip and not is_python and not is_self and not is_inline_cmt:
        return True


def exclude_excluded_pkgs(pkg: str):
    if pkg not in pkgs_to_exclude:
        return True


def strip_non_pkg_chars(pkg):
    return (
        pkg.lstrip("-")  # remove leading dashes from listing packages
        .split("::")[-1]  # on pkgs that specify directly their channel, take pkg, not channel
        .split("#")[0]  # split inline comments and take pkg
        .strip()
    )


def rename_pkgs(pkg):
    if pkg in pkg_renames:
        return pkg_renames[pkg]
    return pkg


def process_file(path):
    with open(path, "r") as f:
        file = f.read()
    deps = file.split("dependencies:")[-1].strip().replace(" ", "").splitlines()
    deps = [dep for dep in deps if dep.startswith("-")]
    almost_pkgs = filter(remove_non_pkgs, deps)
    pkgs = map(strip_non_pkg_chars, almost_pkgs)
    pkgs = filter(exclude_excluded_pkgs, pkgs)
    pkgs = map(rename_pkgs, pkgs)
    return list(pkgs)


pkgs_to_exclude = list(map(strip_non_pkg_chars, pkgs_to_exclude))

base_pkgs = process_file(BASE_ENV)

dev_pkgs = [pkg for pkg in process_file(DEV_ENV) if pkg not in base_pkgs]

setup(
    install_requires=base_pkgs,
    extras_require={"dev": dev_pkgs},
)
