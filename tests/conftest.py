"""Define the project fixture for use with pytest."""

import pytest
from setup_venv import (
    convert_to_src_layout,
    create_base_project,
    run_git,
    use_importlib_metadata_backport,
    use_version_py_build_hook,
)


@pytest.fixture(
    params=[
        pytest.param(("flat", "importlib.metadata"), id="flat-stdlib"),
        pytest.param(("flat", "importlib_metadata"), id="flat-backport"),
        pytest.param(("flat", "_version.py"), id="flat-version-py"),
        pytest.param(("src", "importlib.metadata"), id="src-stdlib"),
        pytest.param(("src", "importlib_metadata"), id="src-backport"),
        pytest.param(("src", "_version.py"), id="src-version-py"),
    ]
)
def project(request):
    """Create a temporary project directory with a clone of the repository.

    This fixture is parametrized to test combinations of:
    - Flat vs src layout
    - Version source: importlib.metadata, importlib_metadata, or _version.py

    The project includes:
    - Fresh clone of the repository
    - New virtual environment
    - Layout and version source based on parameters
    """
    layout, version_source = request.param
    project = create_base_project(request.function.__name__)

    if layout == "src":
        project = convert_to_src_layout(project)
    project["layout"] = layout

    if version_source == "importlib_metadata":
        use_importlib_metadata_backport(project)
    elif version_source == "_version.py":
        use_version_py_build_hook(project)
    project["version_source"] = version_source

    # Create initial commit and tag
    run_git(
        ["commit", "--allow-empty", "-m", "Initial commit for v100.2.3"],
        cwd=project["path"],
    )
    run_git(["tag", "v100.2.3"], cwd=project["path"])
    return project
