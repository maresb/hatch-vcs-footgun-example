import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent


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
    if project["layout"] == "src":
        return project["path"] / "src" / "hatch_vcs_footgun_example"
    return project["path"] / "hatch_vcs_footgun_example"


def use_importlib_metadata_backport(project):
    """Update version.py to use `importlib_metadata` instead of `importlib.metadata`."""
    version_py = get_package_path(project) / "version.py"
    content = version_py.read_text()
    content = content.replace(
        "from importlib.metadata import version",
        "from importlib_metadata import version",
    )
    version_py.write_text(content)
    run_python(
        [project["python"], "-m", "pip", "install", "importlib_metadata"],
        cwd=project["path"],
    )

    # Commit the changes
    run_git(["add", "."], cwd=project["path"])
    run_git(
        ["commit", "-m", "Update version.py to use importlib_metadata backport"],
        cwd=project["path"],
    )


def use_version_py_build_hook(project):
    """Configure the project to use _version.py build hook."""
    # Update pyproject.toml to enable the build hook
    package_path = get_package_path(project)
    relative_package_path = package_path.relative_to(project["path"])
    version_file = relative_package_path / "_version.py"
    pyproject = project["path"] / "pyproject.toml"
    content = pyproject.read_text()
    content += dedent(
        f"""
        [tool.hatch.build.hooks.vcs]
        version-file = "{version_file.as_posix()}"
        """
    )
    pyproject.write_text(content)

    # Update version.py to use _version.py
    version_py = get_package_path(project) / "version.py"
    content = version_py.read_text()

    original_version_definition = "__version__ = _get_importlib_metadata_version()"
    new_version_definition = (
        "from hatch_vcs_footgun_example._version import __version__"
    )
    assert original_version_definition in content
    content = content.replace(original_version_definition, new_version_definition)
    version_py.write_text(content)

    # Add _version.py to .gitignore
    gitignore = project["path"] / ".gitignore"
    content = gitignore.read_text()
    content += "\n_version.py\n"
    gitignore.write_text(content)

    # Commit the changes
    run_git(["add", "."], cwd=project["path"])
    run_git(
        ["commit", "-m", "Configure project to use _version.py build hook"],
        cwd=project["path"],
    )
