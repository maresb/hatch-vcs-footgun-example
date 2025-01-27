import os
import sys
from textwrap import dedent

from setup_venv import get_package_path, install_editable, run_git, run_python


def test_version_without_install(project):
    """Test that running without install raises PackageNotFoundError."""
    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
        check=False,
    )
    assert result.returncode != 0
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
    assert "__package__ not set in" in result.stderr
    assert (
        "ensure that you are running this module as part of a package" in result.stderr
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
