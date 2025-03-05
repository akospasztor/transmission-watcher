#!/usr/bin/env python

import importlib
import os
import pkgutil
import pytest
import re
from setuptools import find_packages

EXCLUDES = []  # Regex: remember to use \. !


root_path = os.path.join(os.path.dirname(__file__), "..")


@pytest.mark.parametrize("package",
                         find_packages(where=root_path,
                                       exclude=['tests', 'tests.*']))
def test_import(package):
    """Test if all (sub-)packages can be imported."""
    module = importlib.import_module(package)
    for _, mod, _ in pkgutil.walk_packages(module.__path__,
                                           prefix="{}.".format(package)):
        if not any([re.search(exclude, mod) for exclude in EXCLUDES]):
            importlib.import_module(mod)
