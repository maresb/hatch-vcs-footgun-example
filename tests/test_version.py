import os
import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest


def run_git(cmd, cwd, check=True):
    """Run a git command and return its output.

    Args:
        cmd: List of command parts
        cwd: Working directory
        check: Whether to check the return code

    Returns:
        The command output if check=True and command succeeds

    Raises:
        subprocess.CalledProcessError if check=True and command fails
    """
    result = subprocess.run(
        ["git"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )
    return result.stdout.strip()


def run_python(cmd, cwd, env=None, check=True):
    """Run a Python command and return its output.

    Args:
        cmd: List of command parts
        cwd: Working directory
        env: Optional environment variables
        check: Whether to check the return code

    Returns:
        CompletedProcess instance
    """
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
        env=env,
    )
    return result


def install_editable(project):
    """Install the project in editable mode for a given venv."""
    run_python(
        [project["python"], "-m", "pip", "install", "-e", "."],
        cwd=project["path"],
    )


def create_base_project(test_name):
    """Create a base project with a fresh clone and venv."""
    # Create temp dir without using context manager so it won't be auto-deleted
    # Include the test name in the prefix for easier debugging
    tmpdir = tempfile.mkdtemp(prefix=f"hatch_vcs_test_{test_name}_")
    print(f"\nTemporary test directory: {tmpdir}")

    # Get the current repo path
    repo_path = Path(__file__).parent.parent.absolute()

    # Clone the current repo into the temp dir
    run_git(["clone", str(repo_path), tmpdir], cwd=".")

    # Configure Git user and email for the cloned repo
    run_git(["config", "user.email", "test@example.com"], cwd=tmpdir)
    run_git(["config", "user.name", "Test User"], cwd=tmpdir)

    # Create and activate a venv
    venv_path = Path(tmpdir) / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

    # Get the Python executable from the venv
    if sys.platform == "win32":
        python = venv_path / "Scripts" / "python.exe"
    else:
        python = venv_path / "bin" / "python"

    # Install hatch-vcs in the venv
    subprocess.run(
        [python, "-m", "pip", "install", "--upgrade", "pip", "hatch-vcs"],
        cwd=tmpdir,
        check=True,
    )

    return {
        "path": Path(tmpdir),
        "python": str(python),
        "venv": venv_path,
    }


def convert_to_src_layout(project):
    """Convert the project from a flat layout to use src/ layout."""
    # Create src directory
    src_dir = project["path"] / "src"
    src_dir.mkdir()

    # Move package into src/
    pkg_dir = project["path"] / "hatch_vcs_footgun_example"
    pkg_dir.rename(src_dir / "hatch_vcs_footgun_example")

    # Update pyproject.toml for src layout
    pyproject = project["path"] / "pyproject.toml"
    content = pyproject.read_text()
    content += dedent(
        """
        [tool.hatch.build.targets.wheel]
        packages = ["src/hatch_vcs_footgun_example"]
        """
    )
    pyproject.write_text(content)
    run_git(["add", "."], cwd=project["path"])
    run_git(
        ["commit", "-m", "Update pyproject.toml for src layout"], cwd=project["path"]
    )
    return project


def get_package_path(project):
    """Get the path to the package directory based on layout."""
    if project.get("layout") == "src":
        return project["path"] / "src" / "hatch_vcs_footgun_example"
    return project["path"] / "hatch_vcs_footgun_example"


@pytest.fixture(params=["flat", "src"])
def project(request):
    """Create a temporary project directory with the specified layout.

    This fixture is parametrized to test both flat and src layouts.
    The project includes:
    - Fresh clone of the repository
    - New virtual environment
    - Either flat or src layout based on the parameter
    """
    base_project = create_base_project(request.function.__name__)

    if request.param == "src":
        updated_project = convert_to_src_layout(base_project)
    else:
        updated_project = base_project

    # Create initial commit and tag
    run_git(
        ["commit", "--allow-empty", "-m", "Initial commit for v100.2.3"],
        cwd=updated_project["path"],
    )
    run_git(["tag", "v100.2.3"], cwd=updated_project["path"])

    updated_project["layout"] = request.param
    return updated_project


def test_version_without_install(project):
    """Test that running without install raises PackageNotFoundError."""
    result = run_python(
        [project["python"], "-m", "hatch_vcs_footgun_example.main"],
        cwd=project["path"],
        check=False,
    )
    assert result.returncode != 0
    if project["layout"] == "flat":
        assert "PackageNotFoundError" in result.stderr
    else:
        assert "Error while finding module specification for" in result.stderr
        assert "ModuleNotFoundError: No module named" in result.stderr


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
    if sys.version_info >= (3, 13):
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
