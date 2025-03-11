#!/usr/bin/env python

import importlib
import os
import pkgutil
import pytest
import re
from setuptools import find_packages

ROOT_PATH = os.path.join(os.path.dirname(__file__), "..")
EXCLUDES = []  # regex format


@pytest.mark.parametrize("package",
                         find_packages(where=ROOT_PATH,
                                       exclude=['tests', 'tests.*']))
def test_import(package):
    """Test if all (sub-)packages can be imported."""
    module = importlib.import_module(package)
    for _, mod, _ in pkgutil.walk_packages(module.__path__,
                                           prefix="{}.".format(package)):
        if not any([re.search(exclude, mod) for exclude in EXCLUDES]):
            importlib.import_module(mod)
