#!/usr/bin/env python3

import io
import os
import re

from setuptools import find_packages, setup


# Get version
def read(*names, **kwargs):
    with io.open(
        os.path.join(os.path.dirname(__file__), *names), encoding=kwargs.get("encoding", "utf8")
    ) as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


readme = open("README.md").read()
version = find_version("optiwrap", "__init__.py")

# set the install requirements
torch_min = "1.9"
install_requires = [
    ">=".join(["torch", torch_min]),
    "gpytorch>=1.5",
    "botorch>=0.5",
    "ax-platform>=0.2.0",
    "scikit-learn",
    "scipy",
    "pandas",
    "numpy",
    "click",
    "PyYAML",
]

# Run the setup
setup(
    name="optiwrap",
    version=version,
    description="An implementation of Gaussian Processes in Pytorch",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Madeline Scyphers, Justine Missik",
    url="https://github.com/madeline-scyphers/optiwrap",
    author_email="madelinescyphers@gmail.com, jemissik@gmail.com",
    project_urls={
        "Source": "https://github.com/madeline-scyphers/optiwrap",
    },
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(exclude=["test", "test.*"]),
    python_requires=">=3.7",
    install_requires=install_requires,
    extras_require={
        "dev": ["black", "black[jupyter]", "isort", "twine", "pre-commit"],
    },
    test_suite="test",
)
