# Hatch VCS Footgun Example

[![GitHub](https://img.shields.io/badge/github-maresb%2Fhatch--vcs--footgun--example-blue)](https://github.com/maresb/hatch-vcs-footgun-example)
[![PyPI - Version](https://img.shields.io/pypi/v/hatch-vcs-footgun-example.svg)](https://pypi.org/project/hatch-vcs-footgun-example)
[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch)
[![License: Unlicense](https://img.shields.io/github/license/maresb/hatch-vcs-footgun-example)](LICENSE)

A somewhat hacky usage of the [Hatch VCS](https://github.com/ofek/hatch-vcs) plugin to ensure that the `__version__` variable stays up-to-date, even when the project is installed in editable mode.

## Quick summary

1. Ensure that [Hatch VCS](https://pypi.org/project/hatch-vcs/) is configured in [`pyproject.toml`](pyproject.toml).
1. Copy the contents of [`version.py`](hatch_vcs_footgun_example/version.py) and adjust to your project.
1. Recommended: import `__version__` from that module into your top-level `__init__.py` file.
1. [Set the `MYPROJECT_HATCH_VCS_RUNTIME_VERSION` environment variable](#setting-the-environment-variable) to anything (e.g. `1`) to enable updating the version number at runtime.

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

   1. Parsing the `METADATA` file can be relatively slow. If performance is crucial and every millisecond of startup time counts (e.g. if one is writing a CLI tool), then this is not an ideal solution.

1. ### Use a static `_version.py` file

   If using the [Hatch VCS build hook](https://github.com/ofek/hatch-vcs#build-hook) option of the `hatch-vcs` plugin, a `_version.py` file will be generated when either building a distribution or installing the project from source.

   Since `_version.py` is generated dynamically, it should be added to `.gitignore`.

   As with the `importlib.metadata` approach, if the project is installed in editable mode then the `_version.py` file will not be updated unless the package is reinstalled (or locally rebuilt).

   For more details, see [the `_version.py` build hook section](#optional-using-the-_versionpy-build-hook).

1. ### Use `hatch-vcs` to dynamically compute the version number at runtime

   This strategy has several requirements:

   1. The `pyproject.toml` file must be present. (This is usually _not_ a viable option because this file is typically absent when a project is installed from a wheel!)
   1. The `hatch-vcs` plugin must be installed. (This is usually only true in the build environment.)
   1. `git` must be available, and the tags must be accessible and up-to-date.

   This is very fragile, but has the advantage that when it works, the version number is always up-to-date, even for an editable installation.

   This method should always be used with a fallback to one of the other two methods to avoid failure when the requirements are not met. For example, a production deployment will typically not have `git`, `hatchling`, or `hatch-vcs` installed.

We recommend a default of using `importlib.metadata` to compute the version number. When more up-to-date version numbers are needed, the `hatch-vcs` method can be enabled by setting the `MYPROJECT_HATCH_VCS_RUNTIME_VERSION` environment variable.

### Optional: Using the `_version.py` build hook

Enabling the `_version.py` build hook has no advantage over `importlib.metadata` in terms of version updates, but it is a viable alternative.

To enable this method, add the following to your `pyproject.toml` file:

```toml
[tool.hatch.build.hooks.vcs]
version-file = "myproject/_version.py"
```

Then in `version.py`, remove `_get_importlib_metadata_version` and replace its invocation with

```python
from myproject._version import __version__
```

## Conclusion

In most cases, using `importlib.metadata.version` is the best solution. However, this data can become outdated during development with an editable install. If reporting the correct version during development is important, then the hybrid approach implemented in [`version.py`](hatch_vcs_footgun_example/version.py) may be desirable:

- Default to using `importlib.metadata.version` to compute the version number.
- Use `hatch-vcs` to update the version number at runtime if `MYPROJECT_HATCH_VCS_RUNTIME_VERSION` is set.

## Why "Footgun"?

Such a hybrid approach to determine the version number is somewhat of a [footgun](https://en.wiktionary.org/wiki/footgun): it involves distinct version detection mechanisms between development and deployment. Ideally you should always remember to reinstall the package whenever checking out a new commit so that you can simply use the standard `importlib.metadata.version` mechanism. In contrast, the hybrid approach is unsupported, so it must be used at your own risk.

Earlier versions of this project were significantly more fragile because they tried to guess whether or not the project was being run in a development environment. Thanks to community feedback, the current version is much less of a footgun.

## Usage

After cloning this repository,

```bash
# Fix an initial version number
git commit --allow-empty -m "For v100.2.3"
git tag v100.2.3
# Try to run the package without installing it
python -m hatch_vcs_footgun_example.main  # Fails with PackageNotFoundError
# Install the package
pip install --editable .
# Run the package
python -m hatch_vcs_footgun_example.main  # Prints "My version is '100.2.3'."
```

Without setting the environment variable, the version number is reported incorrectly after a new tag.

```bash
git commit --allow-empty -m "For v100.2.4"
git tag v100.2.4
unset MYPROJECT_HATCH_VCS_RUNTIME_VERSION  # Just in case it was previously set
python -m hatch_vcs_footgun_example.main  # My version is '100.2.3'.
```

After setting the environment variable, the version number is correctly reported:

```bash
export MYPROJECT_HATCH_VCS_RUNTIME_VERSION=1
python -m hatch_vcs_footgun_example.main  # My version is '100.2.4'.
```

## Setting the environment variable

There are several ways to set `MYPROJECT_HATCH_VCS_RUNTIME_VERSION` in your development environment:

- **Shell configuration** (`.bashrc`, `.zshrc`, etc.):

  ```bash
  export MYPROJECT_HATCH_VCS_RUNTIME_VERSION=1
  ```

- **[direnv](https://direnv.net/)** (`.envrc` in your project root):

  ```bash
  export MYPROJECT_HATCH_VCS_RUNTIME_VERSION=1
  ```

- **[Hatch](https://hatch.pypa.io/latest/config/environment/advanced/#environment-variable-overrides)** (`pyproject.toml` or `hatch.toml`):

  ```toml
  [tool.hatch.envs.default.env-vars]
  MYPROJECT_HATCH_VCS_RUNTIME_VERSION = "1"
  ```

- **[conda](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#setting-environment-variables)**:

  ```bash
  conda env config vars set MYPROJECT_HATCH_VCS_RUNTIME_VERSION=1
  ```

- **[pixi](https://pixi.sh/)** (`pixi.toml`):

  ```toml
  [activation.env]
  MYPROJECT_HATCH_VCS_RUNTIME_VERSION = "1"
  ```

- **[Dev Containers](https://containers.dev/implementors/json_reference/#general-properties)** (`.devcontainer/devcontainer.json`):

  ```json
  {
    "containerEnv": {
      "MYPROJECT_HATCH_VCS_RUNTIME_VERSION": "1"
    }
  }
  ```

## Troubleshooting

There are many potential pitfalls to this approach. Please open an issue if you encounter one not covered here, or if the solution is insufficient.

- ### The version number computed by `hatch-vcs` is incorrect

  Ensure that your clone of the repository has the latest tags. You may need to run

  ```bash
  git pull --tags
  ```

- ### `PackageNotFoundError` / `ModuleNotFoundError: No module named ...`

  This occurs when the package is not installed. With a `src/` layout, you may see `ModuleNotFoundError` instead. Install the package first:

  ```bash
  pip install --editable .
  ```

- ### `ModuleNotFoundError: No module named '..._version'`

  This occurs when using the `_version.py` build hook but running from source without installing. The `_version.py` file is generated during install/build.

  Install the package (editable or otherwise) to generate it.

- ### `Unknown version source: vcs`

  This occurs when `MYPROJECT_HATCH_VCS_RUNTIME_VERSION` is set but `hatch-vcs` is not installed.

  Either install `hatch-vcs` in your environment, or unset the environment variable if you don't need runtime version updates.

- ### `RuntimeError: __package__ not set in '...'`

  This occurs when running the script directly instead of as a module.

  Correct:

  ```bash
  python -m mypackage.main
  ```

  Incorrect:

  ```bash
  python mypackage/main.py
  ```

  (The latter should only be used for running scripts that are not part of a package!)

- ### `LookupError: Error getting the version from source `vcs`: setuptools-scm was unable to detect version`

  This occurs when `MYPROJECT_HATCH_VCS_RUNTIME_VERSION` is set but `git` is not correctly installed.

  Either ensure `git` is available, or unset the environment variable.

- ### `ImportError: cannot import name '__version__' from partially initialized module '...' (most likely due to a circular import)`

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

- ### `ModuleNotFoundError: No module named 'importlib.metadata'`

  For end-of-life versions of Python below 3.8, the `importlib.metadata` module is not available. In this case, you need to install the `importlib-metadata` backport and
  fall back to `importlib_metadata` in place of `importlib.metadata`.
