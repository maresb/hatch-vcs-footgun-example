# Hatch VCS Footgun Example

[![PyPI - Version](https://img.shields.io/pypi/v/hatch-vcs-footgun-example.svg)](https://pypi.org/project/hatch-vcs-footgun-example)
[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch)
[![License: Unlicense](https://img.shields.io/github/license/maresb/hatch-vcs-footgun-example)](LICENSE)

A somewhat hacky usage of the [Hatch VCS](https://github.com/ofek/hatch-vcs) plugin to ensure that the `__version__` variable stays up-to-date, even when the project is installed in editable mode.

## Quick summary

1. Ensure that [Hatch VCS](https://pypi.org/project/hatch-vcs/) is configured in [`pyproject.toml`](pyproject.toml).
1. Copy the contents of [`version.py`](hatch_vcs_footgun_example/version.py) and adjust to your project.
1. Install `hatch-vcs` as a development-only dependency.
1. Enjoy up-to-date version numbers, even in editable mode.

## Background

For consistency's sake, it's good to have a single source of truth for the version number of your project. However, there are at least four common places where the version number commonly appears in modern Python projects:

1. The `version` field of the `[project]` section of `pyproject.toml`.
1. The dist-info `METADATA` file from when the project was installed.
1. The `__version__` variable in the `__init__.py` file of the project's main package.
1. The Git tag of the release commit.

With Hatch VCS, the definitive source of truth is the Git tag. One often still needs a technique to access this version number programmatically. For example, a CLI tool might print its version.

## Standard solutions

1. ### Dynamically read the version number from the package metadata with `importlib.metadata`

   ```python
   # __init__.py
   from importlib.metadata import version

   __version__ = version("myproject")
   ```

   This works well in most cases, and does *not* require the Hatch VCS plugin. If your project is properly installed, you can even replace `"myproject"` with `__package__`.

   There are two important caveats to this approach.

   1. The version number comes from the last time the project was installed. In case you are developing your project in editable mode, the reported version may be outdated unless you remember to reinstall each time the version number changes.

   2. Parsing the `METADATA` file can be relatively slow. If performance is crucial and every millisecond of startup time counts (e.g. if one is writing a CLI tool), then this is not an ideal solution.

1. ### Use a static `_version.py` file

   If using the [Hatch VCS build hook](https://github.com/ofek/hatch-vcs#build-hook) option of the `hatch-vcs` plugin, a `_version.py` file will be generated when either building a distribution or installing the project from source.

   Since `_version.py` is generated dynamically, it should be added to `.gitignore`.

   As with the `importlib.metadata` approach, if the project is installed in editable mode then the `_version.py` file will not be updated unless the package is reinstalled (or locally rebuilt).

1. ### Use `hatch-vcs` to dynamically compute the version number at runtime

   This strategy has several requirements:

   1. The `pyproject.toml` file must be present. (This is usually _not_ a viable option because this file is typically absent when a project is installed from a wheel!)
   2. The `hatch-vcs` plugin must be installed. (This is usually only true in the build environment.)
   3. `git` must be available, and the tags must be accessible and up-to-date.

   This is very fragile, but has the advantage that when it works, the version number is always up-to-date, even for an editable installation.

   This method should always be used with a fallback to one of the other two methods to avoid failure when the requirements are not met. For example, a production deployment will typically not have `git`, `hatchling`, or `hatch-vcs` installed.

## Troubleshooting

There are many potential pitfalls to this approach. Please open an issue if you encounter one not covered here, or if the solution is insufficient.

* ### The version number computed by `hatch-vcs` is incorrect

   Ensure that your clone of the repository has the latest tags. You may need to run

   ```bash
   git pull --tags
   ```

* ### `Unknown version source: vcs`

   Install `hatch-vcs` in your development environment.

   If you see this in your production environment, then uninstall `hatchling`.

* ### `ValueError: A distribution name is required.`

   This occurs when the `__package__` variable is not set. Always ensure that you invoke your package as a module.

   Correct:

   ```bash
   python -m mypackage.main
   ```

   Incorrect:

   ```bash
   python mypackage/main.py
   ```

   (The latter should only be used for running scripts that are not part of a package!)

* ### `LookupError: Error getting the version from source `vcs`: setuptools-scm was unable to detect version`

   This can occur if `git` is not correctly installed.

* ### `ImportError: cannot import name '__version__' from partially initialized module '...' (most likely due to a circular import)`

   This can occur when importing `__version__` from the top-level `__init__.py` file.

   Instead, import `__version__` from `version.py`.

   For example, the following is a classical circular import:

   ```python
   # __init__.py
   import myproject.initialize
   from myproject.version import __version__
   ```

   ```python
   # initialize.py
   from myproject import __version__
   print(f"{__version__=}")
   ```

   while the following is not:

   ```python
   # __init__.py
   import myproject.initialize
   from myproject.version import __version__
   ```

   ```python
   # initialize.py
   from myproject.version import __version__  # Always import from version.py!
   print(f"{__version__=}")
   ```

* ### `ImportError: attempted relative import with no known parent package`

   Ensure that the project is properly installed, e.g. by running `pip install -editable .`.

* ### `ModuleNotFoundError: No module named 'importlib.metadata'`

   For end-of-life versions of Python below 3.8, the `importlib.metadata` module is not available. In this case, you need to install the `importlib-metadata` backport and
   fall back to `importlib_metadata` in place of `importlib.metadata`.

## Conclusion

In most cases, using `importlib.metadata.version` is the best solution. However, this data can become outdated during development with an editable install. If reporting the correct version during development is important, then the hybrid approach implemented in [`version.py`](hatch_vcs_footgun_example/version.py) may be desirable:

- Default to using `hatch-vcs` to compute the version number at runtime.
- Fall back to using `importlib.metadata.version` if `hatchling` is not installed.

## Why "Footgun"?

This hybrid approach is somewhat of a [footgun](https://en.wiktionary.org/wiki/footgun): it involves distinct version detection mechanisms between development and deployment. Ideally you should always remember to reinstall the package whenever checking out a new commit so that you can simply use the standard `importlib.metadata.version` mechanism. In constrast, the hybrid approach is unsupported, so it must be used at your own risk.

## Usage

After cloning this repository,

```bash
python -m hatch_vcs_footgun_example.main  # PackageNotFoundError because it's not installed
pip install --editable .
python -m hatch_vcs_footgun_example.main  # Prints "My version is '1.0.3'."
```

Without `hatch-vcs` installed, the version number is reported incorrectly after a new tag.

```bash
git commit --allow-empty -m "For v1.2.3"
git tag v1.2.3
python -m hatch_vcs_footgun_example.main  # My version is '1.0.3'.
```

With `hatch-vcs` installed the version is correctly reported:

```bash
pip install hatch-vcs
python -m hatch_vcs_footgun_example.main  # My version is '1.2.3'.
```
