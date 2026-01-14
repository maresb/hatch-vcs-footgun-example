"""Project initialization.

It is a popular convention to define `__version__` in the top-level `__init__.py`.
"""

# Importing __version__ from version.py rather than computing it here
# helps to avoid circular imports.
from hatch_vcs_footgun_example.version import __version__

__all__ = ["__version__"]
