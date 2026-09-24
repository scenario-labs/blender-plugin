# Validation and local commands

See [the environment reference](../../CONTRIBUTING.md#environment-variables) for
developer credentials and explicit live commands.

Use the uv version required by `pyproject.toml`. Run `uv sync --locked` to create
the worktree's `.venv` from `uv.lock` and the interpreter in `.python-version`.
`make test` runs `uv run --locked --no-env-file python -m pytest`; use the same prefix for
focused tests. Development dependencies belong in `[dependency-groups].dev`;
commit the updated lockfile when changing them. Do not maintain a parallel
requirements-dev.txt or install ad hoc tools into the managed environment.
For an explicit interpreter check, use `uv run --locked --python <version>`.
Blender native tests still use Blender's bundled Python and an isolated profile.
Preserve exit codes when capturing logs, and distinguish passed checks from
checks that were not run.

[Unit-test CI](../../.github/workflows/unit-tests.yml) runs the complete unit suite
on pinned Python 3.11 and 3.13 interpreters with the same locked dependencies and
dotenv loading disabled. It needs no credentials. The existing SDK-contract and
Blender-baseline check names remain available; a combined required-check gate
and coverage reporting are still tracked in #27 and #45.

An autouse fixture rejects non-loopback `socket.connect` and `connect_ex` calls
in each unit test. Loopback TCP and Unix sockets remain available for local MCP
tests. `@pytest.mark.allow_network` explicitly opts a test out; unknown markers
fail collection. This catches accidental service connections in the pytest
process, not DNS lookups, subprocesses or arbitrary network code. Paid/live
checks belong in their separate opt-in tools, never the default unit suite.

Use the pinned Ruff configuration before further Python development:
`make format` applies safe fixes and formatting; `make lint` checks both.
During Studio adoption, scope these commands with `LINT_PATHS` to changed or
adopted files. CI checks whole changed Python files; full-tree findings remain
tracked in #28 until the dedicated mechanical normalization. Do not reformat
obsolete prototypes as unrelated cleanup. Follow `docs/PYTHON_STYLE.md`,
including Blender registration/annotation cautions, and keep any eventual
pre-commit hook version aligned with the required Ruff version.

`make test-blender` owns fresh disposable profiles for its entire build/install/test
sequence, including probes. It strips inherited credentials and Blender/Python path
overrides, verifies installed ZIP contents and reports actual runtime versions.
See [the native test loop](../../CONTRIBUTING.md#native-blender-test-loop). Use `BLENDER`
or `--blender` to select a supported binary; discovery does not prove compatibility.

The portable build/install tools also create fresh isolated profiles and scrub
inherited credentials and path overrides. For every direct Blender invocation outside these tools,
including probes, export an absolute disposable profile:
`export BLENDER_USER_RESOURCES="$PWD/.blender-profile"`.
Never install development builds into the user's normal profile.

- `make build`: build and validate the extension ZIP; use
  `BLENDER_BUILD_ARGS="--repo"` to also generate a local extension repository.
- `make install`: build and install into a new isolated profile; use
  `BLENDER_INSTALL_ARGS="--launch"` to open it.
- `make test-blender`: build/validate/install an exact ZIP, then run the offline
  baseline in a new profile. No prior installation is needed. Logs and ZIP remain
  under `.blender-profile/run-*`; successful profiles are removed. Use
  `BLENDER_TEST_ARGS="--suite all"` for the full existing integration suite.
- For package changes, inspect the resulting ZIP, validate it and check its
  license content. Keep root `LICENSE` and `scenario/LICENSE` identical.
- For UI changes, exercise native behavior and inspect captured screenshots.
  Report actual Blender/OS versions and limitations.
- For instruction or documentation changes, check links, symlinks, commands and
  the diff. Do not run the full Blender suite just to populate a test count.
- Smoke tests, generation, prompt helpers and scene design can spend credits.
  Do not run them as part of a documentation command.

Use `blender --background scene.blend --command scenario_blender` for local MCP.
Set `SCENARIO_BLENDER_TOKEN` for an explicit token, or use the generated session
token shown at startup. Online access must be enabled; SIGINT/SIGTERM stop the
server cleanly. Run it only in the isolated development profile described above.
