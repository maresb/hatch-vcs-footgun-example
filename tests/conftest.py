"""Define the project fixture for use with pytest."""

import pytest
from setup_venv import (
    convert_to_src_layout,
    create_base_project,
    run_git,
    use_importlib_metadata_backport,
)


@pytest.fixture(
    params=[
        pytest.param(("flat", "importlib.metadata"), id="flat-stdlib"),
        pytest.param(("flat", "importlib_metadata"), id="flat-backport"),
        pytest.param(("src", "importlib.metadata"), id="src-stdlib"),
        pytest.param(("src", "importlib_metadata"), id="src-backport"),
    ]
)
def project(request):
    """Create a temporary project directory with a clone of the repository.

    This fixture is parametrized to test combinations of:
    - Flat vs src layout
    - importlib.metadata vs importlib_metadata

    The project includes:
    - Fresh clone of the repository
    - New virtual environment
    - Layout and importlib.metadata or importlib_metadata module based on parameters
    """
    layout, metadata_module = request.param
    project = create_base_project(request.function.__name__)

    if layout == "src":
        project = convert_to_src_layout(project)
    project["layout"] = layout

    if metadata_module == "importlib_metadata":
        use_importlib_metadata_backport(project)
    project["metadata_module"] = metadata_module

    # Create initial commit and tag
    run_git(
        ["commit", "--allow-empty", "-m", "Initial commit for v100.2.3"],
        cwd=project["path"],
    )
    run_git(["tag", "v100.2.3"], cwd=project["path"])
    return project
