# Python linting and formatting

Use Ruff for linting, import sorting, safe automatic fixes and formatting.
[pyproject.toml](../pyproject.toml) is the shared configuration for editors,
contributors, agents and CI. Its required version matches the exact Ruff pin in
[requirements-dev.txt](../requirements-dev.txt); upgrade both together.

## Setup and commands

Create a development environment with Python 3.11 or later:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
make lint PYTHON=.venv/bin/python
make format PYTHON=.venv/bin/python
make test PYTHON=.venv/bin/python
```

On Windows, use `.venv\Scripts\python.exe -m pip`, `-m ruff` and `-m pytest`
directly, or use Make from a compatible shell. With an activated environment,
the normal commands are:

```sh
ruff check .
ruff format --check .
ruff check --fix .
ruff format .
```

`make format` attempts safe lint fixes and formatting, then fails if lint
findings still need manual attention. Review the diff and run the relevant
tests. Do not enable unsafe fixes as a routine cleanup step. Neither linting nor
formatting needs Blender, a Scenario account or network service calls.

## Policy

- Four spaces, double quotes, LF endings and a 100-character formatting target,
  matching Studio's line length. Long strings/comments may exceed the target.
- Python errors and unused names (`E4/E7/E9/F`), import sorting (`I`), common bug
  patterns (`B`), compatible syntax modernization (`UP`) and stale suppressions
  (`RUF100`). Add focused rules when they catch a demonstrated problem.
- `py311` is deliberate: Blender 5.0.1's [tagged build configuration](https://github.com/blender/blender/blob/v5.0.1/build_files/build_environment/cmake/versions.cmake)
  specifies Python 3.11.13. Blender 5.1 upgrades to Python 3.13. Keep syntax
  compatible with the oldest supported interpreter; linting does not verify
  Blender API or bundled dependency compatibility on 5.0, 5.1 and 5.2.
- Keep Blender property declarations evaluated at registration. Do not add
  postponed annotations to modules with `bpy.props` declarations just to satisfy
  a style suggestion. Review import cleanup for registration side effects.
- Use narrow suppressions with a reason. The configured `E402` exceptions cover
  standalone scripts that establish their import path before importing the
  package; there is no package-wide exception for Blender modules.
- Exclude retired `archive/` and `versions/` snapshots and disposable Blender
  profiles. Do not format third-party dependency sources or generated bundles.
  Add their concrete paths to exclusions when SDK packaging establishes them.

## Studio adoption transition

This configuration does not imply that the existing prototype passes lint.
`make lint` checks the full tree and reports its existing findings. During
adoption, work on the retained/adopted files with, for example:

```sh
make format LINT_PATHS="scenario/core/jobs tests/unit/test_manager.py"
make lint LINT_PATHS="scenario/core/jobs tests/unit/test_manager.py"
```

[Python lint CI](../.github/workflows/python-lint.yml) enforces the same rules on
all added/modified Python files in a PR, including their unchanged lines. This
temporary scope avoids a mechanical rewrite of prototype code scheduled for
replacement. Keep this transition visible in [#28](https://github.com/scenario-labs/blender-plugin/issues/28)
and [#64](https://github.com/scenario-labs/blender-plugin/issues/64).

Normalize adopted Studio code in a dedicated mechanical PR before functional
changes. Preserve provenance and licenses, run the appropriate tests, then
switch CI to full-tree `make lint`. Record the merged formatting commit in
`.git-blame-ignore-revs` after its final squash SHA exists. Optional pre-commit
hooks remain tracked in #30 and must use the same Ruff pin and configuration.
