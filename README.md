# Hatch VCS Footgun Example

[![PyPI - Version](https://img.shields.io/pypi/v/hatch-vcs-footgun-example.svg)](https://pypi.org/project/hatch-vcs-footgun-example)
[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch)
[![License: Unlicense](https://img.shields.io/github/license/maresb/hatch-vcs-footgun-example)](LICENSE)

A somewhat hacky usage of the [Hatch VCS build hook](https://github.com/ofek/hatch-vcs#build-hook) which ensures that the `__version__` variable stays up-to-date, even when the project is installed in editable mode.

## Quick summary

1. Ensure that [Hatch VCS](https://pypi.org/project/hatch-vcs/) is configured in [`pyproject.toml`](pyproject.toml).
1. Copy the contents of [`__init__.py`](hatch_vcs_footgun_example/__init__.py) and adjust to your project.
1. Add `_version.py` to your [`.gitignore`](.gitignore) file.
1. Install `setuptools-scm` as a development dependency.
1. Enjoy up-to-date version numbers, even in editable mode.

## Background

For consistency's sake, it's good to have a single source of truth for the version number of your project. There are three common places where the version number appears in most modern Python projects:

1. The `version` field of the `[project]` section of `pyproject.toml`.
1. The `__version__` variable in the `__init__.py` file of the project's main package.
1. The Git tag of the release commit.

With Hatch VCS, the single source of truth is the Git tag. One often still needs a technique to access this version number programmatically. The [quasi-standard](https://stackoverflow.com/a/459185) is to store it in the `__version__` variable, so that the following works:

```python
import myproject

print(myproject.__version__)
```

## Standard solutions

1. ### Dynamically read the version number from the package metadata with `importlib.metadata`

   For Python 3.8 and higher, one can do:

   ```python
   # __init__.py
   from importlib.metadata import version

   __version__ = version("myproject")
   ```

   This works well in most cases, and does *not* require the Hatch VCS build hook.

   A downside is that this is relatively slow. If performance is crucial and every millisecond counts (e.g. if one is writing a CLI tool), then this is not an ideal solution.

   (For compatibility with Python 3.7 and lower, see [the examples here](https://packaging.python.org/en/latest/guides/single-sourcing-package-version/) regarding `importlib_metadata`.)

1. ### Use a static `_version.py` file

   Using the [Hatch VCS build hook](https://github.com/ofek/hatch-vcs#build-hook), a `_version.py` file is generated when either building a distribution or installing the project from source.

   ```python
   # __init__.py
   from myproject._version import __version__
   ```

   Since `_version.py` is generated dynamically, it should be added to `.gitignore`.

   One disadvantage in certain situations (e.g. collaborative team development) is that if the project is installed in editable mode, then the `_version.py` file will not be updated unless the package is reinstalled or locally rebuilt.

1. ### Compute the version number at runtime with `setuptools_scm`

   Using `setuptools_scm` as follows only succeeds in particular cases:

   ```python
   from setuptools_scm import get_version

   __version__ = get_version(root="..", relative_to=__file__)
   ```

   It requires that `setuptools_scm` is installed in the runtime environment alongside the VCS tool (`git` or `hg`), and in order to read the tags, the project must be installed from a source repository.

   This is very fragile, but has the advantage that when it works, the version number is always up-to-date, even for an editable installation.

## Conclusion

In most cases, using `importlib.metadata` or `_version.py` are the best solutions. In the second case, the Hatch VCS build hook is a good way to generate the `_version.py` file.

## Why "Footgun"?

In case you are developing in editable mode, and it is important that the version number be kept up-to-date automatically, then it is possible to use a solution similar to that illustrated in this example. Namely:

- Default to using `setuptools_scm` to set `__version__`.
- When that fails, fall back to `_version.py`.

However, it is somewhat of a [footgun](https://en.wiktionary.org/wiki/footgun): it involves distinct version detection mechanisms between development and deployment. Furthermore, this technique is unsupported, so it must be used at your own risk.

## Usage

After cloning this repository,

```bash
python -m hatch_vcs_footgun_example.main  # Prints an error because it's not installed
pip install --editable .  # Installs and creates the "_version.py" file
python -m hatch_vcs_footgun_example.main  # Prints "My version is '1.0.2'."
```

Without `setuptools-scm` installed, the version number is reported incorrectly after a new tag.

```bash
git commit --allow-empty -m "For v1.2.3"
git tag v1.2.3
python -m hatch_vcs_footgun_example.main  # My version is '1.0.2'.
```

With `setuptools-scm` installed the version is correctly reported:

```bash
pip install setuptools-scm
python -m hatch_vcs_footgun_example.main  # My version is '1.2.3'.
```
