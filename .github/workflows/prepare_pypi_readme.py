"""Initialize the pyproject.toml file for hatch-fancy-pypi-readme."""

import tomli_w
import tomllib

with open("pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

del pyproject["project"]["readme"]
dynamic = pyproject["project"].get("dynamic", [])
if "readme" not in dynamic:
    dynamic.append("readme")
pyproject["project"]["dynamic"] = dynamic

pyproject["project"]["license"] = {"file": "LICENSE"}
pyproject["project"]["urls"] = {
    "Homepage": "https://github.com/maresb/hatch-vcs-footgun-example"
}

build_system_requires = pyproject["build-system"].get("requires", [])
if "hatch-fancy-pypi-readme" not in build_system_requires:
    build_system_requires.append("hatch-fancy-pypi-readme")
pyproject["build-system"]["requires"] = build_system_requires

FOOTER = r"""
[tool.hatch.metadata.hooks.fancy-pypi-readme]
content-type = "text/markdown"

[[tool.hatch.metadata.hooks.fancy-pypi-readme.fragments]]
path = "README.md"

[[tool.hatch.metadata.hooks.fancy-pypi-readme.substitutions]]
# Non-image relative links map to the normal absolute GitHub URL
# <https://stackoverflow.com/a/46875147>
pattern = '\[(.*?)\]\(((?!https?://)\S+)\)'
replacement='[\1](https://github.com/maresb/hatch-vcs-footgun-example/tree/main/\g<2>)'
"""

with open("pyproject.toml", "wb") as f:
    tomli_w.dump(pyproject, f)
    f.write(FOOTER.encode("utf-8"))
