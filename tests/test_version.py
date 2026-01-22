import os
import sys
from textwrap import dedent

import pytest

from setup_venv import (  # isort: skip
    get_package_path,
    install_editable,
    run_git,
    run_python,
)


def test_version_without_install(project):
    """Test that running without install raises PackageNotFoundError."""
    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
        check=False,
    )
    assert result.returncode != 0
    if project["version_source"] == "_version.py":
        assert "ModuleNotFoundError: No module named" in result.stderr
    else:
        if project["layout"] == "src":
            assert "Error while finding module specification for" in result.stderr
            assert "ModuleNotFoundError: No module named" in result.stderr
        else:
            assert "PackageNotFoundError" in result.stderr


def test_version_with_install(project):
    """Test that installing the package allows version to be read."""
    install_editable(project)

    # Run the main script
    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
    )
    assert "My version is '100.2.3'" in result.stdout


def test_version_with_new_tag(project):
    """Test version behavior when adding a new tag."""
    install_editable(project)

    # Create a new commit and tag
    run_git(["commit", "--allow-empty", "-m", "Test commit"], cwd=project["path"])
    run_git(["tag", "v100.2.4"], cwd=project["path"])

    # Create clean environment without HATCH_VCS_RUNTIME_VERSION
    env = os.environ.copy()
    env.pop("MYPROJECT_HATCH_VCS_RUNTIME_VERSION", None)  # Remove if present

    # Run without HATCH_VCS_RUNTIME_VERSION - should show old version
    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
        env=env,
    )
    assert "My version is '100.2.3'" in result.stdout

    # Run with HATCH_VCS_RUNTIME_VERSION set - should show new version
    env["MYPROJECT_HATCH_VCS_RUNTIME_VERSION"] = "1"
    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
        env=env,
    )
    assert "My version is '100.2.4'" in result.stdout


def test_no_version_tags(project):
    """Test that setuptools-scm falls back to '0.1.dev...' when no tags exist."""
    # Delete ALL tags so the repo has no version tags at all
    tags = run_git(["tag", "-l"], cwd=project["path"]).splitlines()
    for tag in tags:
        if tag.strip():
            run_git(["tag", "-d", tag.strip()], cwd=project["path"])

    # Verify no tags remain
    remaining_tags = run_git(["tag", "-l"], cwd=project["path"])
    assert remaining_tags.strip() == "", f"Tags still exist: {remaining_tags}"

    install_editable(project)

    # Run with HATCH_VCS_RUNTIME_VERSION set
    env = os.environ.copy()
    env["MYPROJECT_HATCH_VCS_RUNTIME_VERSION"] = "1"
    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
        env=env,
    )

    assert "My version is '0.1.dev" in result.stdout


def test_unknown_version_source(project):
    """Test error when hatch-vcs is uninstalled."""
    install_editable(project)

    # Uninstall hatch-vcs
    run_python(
        [project["python"], "-m", "pip", "uninstall", "-y", "hatch-vcs"],
        cwd=project["path"],
    )

    # Run with HATCH_VCS_RUNTIME_VERSION unset - should succeed
    env = os.environ.copy()
    env.pop("MYPROJECT_HATCH_VCS_RUNTIME_VERSION", None)
    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
        env=env,
    )
    assert result.returncode == 0
    assert "My version is '100.2.3'" in result.stdout

    # Run with HATCH_VCS_RUNTIME_VERSION set - should fail
    env["MYPROJECT_HATCH_VCS_RUNTIME_VERSION"] = "1"
    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
        env=env,
        check=False,
    )
    assert result.returncode != 0
    assert "Unknown version source: vcs" in result.stderr


def test_git_unavailable(project):
    """Test error when git is unavailable (LookupError from setuptools-scm).

    This tests the troubleshooting item:
    'LookupError: Error getting the version from source `vcs`:
    setuptools-scm was unable to detect version'
    """
    install_editable(project)

    # Rename .git directory so setuptools-scm can't find the repo.
    # The project fixture provides an isolated temp directory, so this is safe.
    (project["path"] / ".git").rename(project["path"] / ".git_hidden")

    env = os.environ.copy()
    env["MYPROJECT_HATCH_VCS_RUNTIME_VERSION"] = "1"

    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
        env=env,
        check=False,
    )

    assert result.returncode != 0
    assert "LookupError" in result.stderr
    assert "setuptools-scm was unable to detect version" in result.stderr


def test_run_script_directly(project):
    """Test error when running script directly instead of as module."""
    # Get the correct path to version.py based on layout
    version_py = get_package_path(project) / "version.py"

    # Try to run version.py directly without installing
    result = run_python(
        [project["python"], str(version_py)],
        cwd=project["path"],
        check=False,
    )
    print("\nScript output:")
    print(result.stdout)
    print("\nScript error:")
    print(result.stderr)
    assert result.returncode != 0
    if project["version_source"] == "_version.py":
        assert "ModuleNotFoundError: No module named" in result.stderr
    else:
        assert "__package__ not set in" in result.stderr
        assert (
            "ensure that you are running this module as part of a package"
            in result.stderr
        )


def test_circular_import(project):
    """Test error with circular imports."""
    # Get the correct path to package files based on layout
    pkg_path = get_package_path(project)

    # Create a module that imports incorrectly from the root module instead of
    # from version.py
    bad_module = pkg_path / "initialize.py"
    bad_module.write_text(
        dedent(
            """
            from hatch_vcs_footgun_example import __version__

            print(f"{__version__=}")
            """
        )
    )

    # Update __init__.py to import the bad module
    init_file = pkg_path / "__init__.py"
    init_file.write_text(
        dedent(
            """
            import hatch_vcs_footgun_example.initialize
            from hatch_vcs_footgun_example.version import __version__
            """
        )
    )

    # Install the package
    install_editable(project)

    # Try to import the module - should fail with circular import
    result = run_python(
        [project["python"], "-c", "import hatch_vcs_footgun_example"],
        cwd=project["path"],
        check=False,
    )
    assert result.returncode != 0

    expected_strings = ["ImportError: cannot import name '__version__' from "]
    if sys.version_info >= (3, 13) and project["layout"] != "src":
        expected_strings += [
            "(consider renaming ",
            "if it has the same name as a library you intended to import)",
        ]
    else:
        expected_strings += [
            "partially initialized module",
            "(most likely due to a circular import)",
        ]
    for expected_string in expected_strings:
        assert expected_string in result.stderr


def test_cwd_not_in_project_root(project):
    """Test runtime version computation when cwd != project root.

    `_get_hatch_version()` uses Hatchling's `ProjectMetadata`, which can execute
    Hatch metadata hooks (notably `hatch-fancy-pypi-readme`) while evaluating
    dynamic fields. Those hooks are written for the PEP 517 build environment,
    where the frontend is required to set the current working directory to the
    project root.

    When this version computation is triggered at runtime from some other cwd,
    hooks may look for files like `README.md` relative to the *current cwd* and
    fail with errors like:

    - `ConfigurationError: ["Fragment file 'README.md' not found."]`

    To avoid surprising failures, runtime version computation must ensure
    PEP 517-like behavior by temporarily chdir'ing to the project root while
    reading `ProjectMetadata`.
    """
    # Skip _version.py variant - it doesn't use _get_hatch_version at runtime
    if project["version_source"] == "_version.py":
        pytest.skip("_version.py doesn't use runtime hatch version computation")

    # Configure hatch-fancy-pypi-readme to trigger the cwd bug
    pyproject = project["path"] / "pyproject.toml"
    content = pyproject.read_text()

    # Add hatch-fancy-pypi-readme to build requirements
    content = content.replace(
        'requires = ["hatchling", "hatch-vcs"]',
        'requires = ["hatchling", "hatch-vcs", "hatch-fancy-pypi-readme"]',
    )

    # Change readme from static to dynamic
    content = content.replace('readme = "README.md"', "")
    if '"readme"' not in content:
        content = content.replace(
            'dynamic = ["version"]', 'dynamic = ["version", "readme"]'
        )

    # Add hatch-fancy-pypi-readme configuration
    content += dedent(
        """
        [tool.hatch.metadata.hooks.fancy-pypi-readme]
        content-type = "text/markdown"

        [[tool.hatch.metadata.hooks.fancy-pypi-readme.fragments]]
        path = "README.md"
        """
    )
    pyproject.write_text(content)

    # Install hatch-fancy-pypi-readme in the venv, then install the project
    run_python(
        [project["python"], "-m", "pip", "install", "hatch-fancy-pypi-readme"],
        cwd=project["path"],
    )
    install_editable(project)

    # Create a subdirectory to run from
    notebooks_dir = project["path"] / "notebooks"
    notebooks_dir.mkdir(exist_ok=True)

    # Run with HATCH_VCS_RUNTIME_VERSION set from the subdirectory
    env = os.environ.copy()
    env["MYPROJECT_HATCH_VCS_RUNTIME_VERSION"] = "1"

    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=notebooks_dir,  # Run from subdirectory, not project root
        env=env,
        check=False,
    )

    # Print output for debugging
    print(f"\nstdout: {result.stdout}")
    print(f"\nstderr: {result.stderr}")

    # Should succeed - version should be computed correctly
    # Before the fix, this fails with:
    # ConfigurationError: ["Fragment file 'README.md' not found."]
    assert result.returncode == 0, f"Expected success but got: {result.stderr}"
    assert "My version is '100.2." in result.stdout


def test_missing_tags_cause_incorrect_version(project, tmp_path):
    """Test that missing tags cause hatch-vcs to compute an incorrect version.

    This demonstrates the footgun described in the README: if tags are not fetched
    from the remote, hatch-vcs will compute an incorrect version number.

    The fix is to run `git pull --tags`.

    Equivalent bash session:

    ```bash
    # Setup: project has v100.2.3 tag, installed in editable mode
    cd /tmp && git clone /path/to/project upstream
    cd /path/to/project && git remote add upstream /tmp/upstream

    # Upstream gets a new release
    cd /tmp/upstream
    git commit --allow-empty -m "Test commit for v100.3.0"
    git tag v100.3.0

    # User pulls without --tags (default behavior)
    cd /path/to/project
    git pull upstream main
    export MYPROJECT_HATCH_VCS_RUNTIME_VERSION=1
    python -m hatch_vcs_footgun_example.main
    # Output: My version is '100.2.4.dev1+g...'  (WRONG!)

    # User pulls with --tags (the fix)
    git pull --tags upstream main
    python -m hatch_vcs_footgun_example.main
    # Output: My version is '100.3.0'  (CORRECT)
    ```
    """
    install_editable(project)

    # Get the current branch name
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=project["path"])

    # Set up a non-bare repo as the "upstream" remote
    upstream_dir = tmp_path / "upstream"
    run_git(["clone", str(project["path"]), str(upstream_dir)], cwd=tmp_path)
    run_git(["config", "user.email", "upstream@example.com"], cwd=upstream_dir)
    run_git(["config", "user.name", "Upstream User"], cwd=upstream_dir)
    run_git(["remote", "add", "upstream", str(upstream_dir)], cwd=project["path"])

    # Create a new commit and tag in upstream
    run_git(
        ["commit", "--allow-empty", "-m", "Test commit for v100.3.0"], cwd=upstream_dir
    )
    run_git(["tag", "v100.3.0"], cwd=upstream_dir)

    # Verify project is still at v100.2.3
    env = os.environ.copy()
    env["MYPROJECT_HATCH_VCS_RUNTIME_VERSION"] = "1"
    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
        env=env,
    )
    assert "My version is '100.2.3'" in result.stdout

    # Pull from upstream - by default, git pull does NOT fetch tags
    run_git(["pull", "upstream", branch], cwd=project["path"])

    # Verify we have the commit
    log_output = run_git(["log", "--oneline", "-1"], cwd=project["path"])
    assert "Test commit for v100.3.0" in log_output

    # Version should be INCORRECT - we have the commit but not the tag
    # Without the tag, setuptools-scm computes based on previous tag (100.2.x)
    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
        env=env,
    )
    print(f"\nVersion after pull (default, no tags): {result.stdout}")
    assert "100.3.0" not in result.stdout, f"Should not show 100.3.0: {result.stdout}"
    assert "100.2" in result.stdout, f"Should fall back to 100.2.x: {result.stdout}"

    # Now pull with --tags (the fix from the README)
    run_git(["pull", "--tags", "upstream", branch], cwd=project["path"])

    # Version should now be CORRECT
    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
        env=env,
    )
    print(f"\nVersion after pull --tags: {result.stdout}")
    assert "My version is '100.3.0'" in result.stdout
