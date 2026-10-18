# Python linting and formatting

Use uv to manage the development interpreter, environment and dependencies,
and Ruff for linting, import sorting, safe fixes and formatting.
[pyproject.toml](../pyproject.toml) is the shared configuration for contributors,
agents and CI. [uv.lock](../uv.lock) locks direct and transitive development
dependencies. [.python-version](../.python-version) selects Python 3.11.13,
matching the Python version used by Blender 5.0.1.

## Setup and commands

Install **uv 0.9.26** using the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).
The required uv version is recorded in `[tool.uv]`; CI reads that same pin.
From the repository root:

```sh
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked ruff check --fix .
uv run --locked ruff format .
uv run --locked python -m pytest
```

uv downloads the selected Python if needed and creates `.venv` in the current
checkout or worktree. No environment activation is required. These commands
also work on Windows. The changelog workflow tests additionally require `bash`
and `jq` on PATH; the release workflow tests require `jq`. Make provides the same
workflow:

```sh
make sync
make lint
make format
make test
```

`make format` attempts safe lint fixes and formatting, then fails if lint
findings still need manual attention. Review the diff and run the relevant
tests. Do not enable unsafe fixes as a routine cleanup step. Tests collect the
offline unit and fuzz-harness tests by default; smoke tests need authorization.

The uv project is not built or installed as a Python package (`package = false`).
The `blender-plugin-dev` metadata version is a fixed tooling placeholder;
release automation continues to own the extension version in its existing files.
Blender still loads the extension ZIP with its own Python. The development
lockfile does not establish SDK bundle or native runtime compatibility.

## Dependency changes

Development tools belong in `[dependency-groups].dev`. Use `uv add --dev` or
`uv remove --dev`, and commit both `pyproject.toml` and `uv.lock`. When upgrading
Ruff, update its exact dependency pin and `[tool.ruff].required-version` together.
Use `uv lock --upgrade-package <name>` for an intentional dependency update.

Normal local commands and CI use `--locked`: stale or missing locks fail instead
of silently resolving new versions. Do not maintain a second development
requirements file or install extra packages into `.venv` with pip. Put one-off
tools in a separate environment. Each worktree owns its own `.venv`.

For a deliberate check on another interpreter, use
`uv run --locked --python 3.13 python -m pytest`; this can recreate `.venv`.
Run `uv sync --locked` afterwards to restore the default interpreter. Changing
`.python-version` is a reviewed development-environment update, not a change to
the supported Blender minimum.

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
- Exclude disposable Blender profiles. Do not format third-party dependency
  sources or generated bundles.
  Add their concrete paths to exclusions when SDK packaging establishes them.

## Whole-tree lint

[Python lint CI](../.github/workflows/python-lint.yml) runs `make lint` over the
whole tree on every PR and push to `main`, so every tracked Python file must stay
formatted and lint-clean. Ruff never visits nested agent worktrees under
`.claude/worktrees/`: they are Git-ignored and excluded in `pyproject.toml`, so a
whole-tree `make format` in the main checkout cannot rewrite another agent's
unpushed work. While iterating, scope either command to a few paths:

```sh
make format LINT_PATHS="scenario/core/jobs tests/unit/test_manager.py"
make lint LINT_PATHS="scenario/core/jobs tests/unit/test_manager.py"
```

Format imported or adopted code in a dedicated mechanical PR before functional
changes. Preserve provenance and licenses and run the appropriate tests. Add each
merged mechanical commit to `.git-blame-ignore-revs` once its final squash SHA
exists. GitHub's blame view skips the listed commits; locally, run
`git config blame.ignoreRevsFile .git-blame-ignore-revs` once per clone. The
[optional pre-commit hooks](../CONTRIBUTING.md#optional-local-hooks) run the same
locked Ruff executable on staged Python files. They have no separate Ruff pin.
