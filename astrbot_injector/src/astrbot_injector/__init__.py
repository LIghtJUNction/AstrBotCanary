"""
Taskiq dependencies package.

This package is used to add dependency injection
in your project easily.

Github repo: https://github.com/taskiq-python/taskiq-dependencies
"""

from .dependency import Depends
from .graph import DependencyGraph
from .utils import ParamInfo

__all__ = ["DependencyGraph", "Depends", "ParamInfo"]
