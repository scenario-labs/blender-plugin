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

[CI](../../.github/workflows/ci.yml) runs Python lint, unit tests, SDK contracts,
the Linux/Windows Blender baseline, knowledge checks and agent-skill validation
as reusable workflows on pull requests and pushes to `main`. The `ci-ok` job
waits for all six workloads in that run and passes only when each succeeds;
failed, cancelled, skipped or missing results fail the gate. PR updates cancel
older CI runs for that PR. Concurrency belongs to the caller so reusable
workflows cannot cancel their parent run.

Individual job names can include their caller prefix; artifact names and native
matrix coverage are unchanged. The separate `pr-title` and `commits` checks
remain independent. Making `ci-ok` required and configuring repository rules
remain administrative work under #45; the workflow does not change settings.

[Workflow contract tests](../../tests/unit/test_workflows.py) follow PR callers
into their local reusable workflows and composite actions to check the explicit
read-only/no-secrets convention. They also check distinct declared job contexts
and run the actual `ci-ok` shell with every workload successful, failed,
cancelled, skipped, empty or absent. Every workload must appear in the gate's
dependencies and result inputs. These stdlib checks cover the repository's
block-style workflow subset and reject unsupported trigger/permission forms;
they do not replace general YAML/action validation or GitHub's actual scheduling,
permissions and check-result evidence. The changed-file lint policy remains the
approved transition under #28/#64.

[Weekly OS checks](../../.github/workflows/blender-os.yml) are separate,
informational schedule/manual jobs for Blender 5.1.2 on macOS Apple silicon and
Windows x64. They fetch pinned official archives, run the full installed native
suite in new profiles and retain logs, exact ZIPs and JSON reports for 14 days.
A separate Ubuntu reporter validates both OS identities and completed conclusions
from the current run's latest job results before writing. It covers setup, test,
timeout and artifact failures, retains earlier successful jobs on partial reruns,
and excludes deliberate whole-workflow cancellation. Failure reporting uses
exact-title, paginated issue lookup; a second failure comments on the same open OS
issue. Reporting does not turn a failed job green.
See [matrix maintenance and first-run acceptance](../../CONTRIBUTING.md#bumping-the-blender-matrix).
Local shell/API-fake tests establish failure propagation and deduplication logic;
actual hosted execution and issue creation/commenting require post-merge proof.

[Unit-test CI](../../.github/workflows/unit-tests.yml) runs the complete unit suite
on pinned Python 3.11 and 3.13 interpreters with the same locked dependencies and
dotenv loading disabled. It needs no credentials.

Each unit matrix leg measures statement coverage for `scenario/core` and
`scenario/mcp` using the pinned pytest-cov development dependency and locked
coverage.py version. The log and Actions summary contain per-file totals;
`unit-coverage-3.11` and `unit-coverage-3.13` retain XML and browsable HTML reports
for 14 days, including when tests fail. Coverage is measured without a minimum
threshold. The reports include unexecuted files in those directories; Blender-only
MCP modules can therefore show zero coverage. These reports do not measure native
Blender behavior or subprocess execution and do not prove live service acceptance.

To generate the same XML and HTML reports locally from the repository root:

```sh
uv run --locked --no-env-file python -m pytest tests/unit -rx \
  --cov --cov-report=term --cov-report=xml --cov-report=html
```

Open `htmlcov/index.html` to inspect missing lines. Report paths and `.coverage`
data are ignored by Git. The coverage source root and report scope live in
`pyproject.toml`, so `--cov` needs no value; reports store relative source paths
for portability and preserve distinct `core/` and `mcp/` filenames.

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
including Blender registration/annotation cautions. The optional pre-commit hooks
use this same locked Ruff executable on staged files. Install with `make hooks`
or the [portable uv command](../../CONTRIBUTING.md#optional-local-hooks).

`make check-rules` runs the currently implemented offline house rules. Its
`actions-pinned` rule checks remote workflow and composite-action references;
the unit suite exercises failures and checks the repository, so no extra CI
job is needed. See [the contribution guide](contributions.md#github-actions-updates)
for supported declaration syntax, explicit file selection and remaining scope.

`make test-blender` owns fresh disposable profiles for its entire build/install/test
sequence, including probes. It strips inherited credentials and Blender/Python path
overrides, verifies installed ZIP contents and reports actual runtime versions.
See [the native test loop](../../CONTRIBUTING.md#native-blender-test-loop). Use `BLENDER`
or `--blender` to select a supported binary; discovery does not prove compatibility.
`uv run --locked --no-env-file python tools/blender_env.py` prints the selected
executable without launching it. Pass `--blender PATH` to override `BLENDER`;
an invalid explicit selection exits with status 1 and a diagnostic rather than
falling back to another installation. `--manifest-version` (also `--version`)
prints the extension version without requiring Blender. See the
[discovery reference](../../CONTRIBUTING.md#native-blender-test-loop) for locations
and version ordering.

| Environment | Available checks | Limits |
| --- | --- | --- |
| Desktop with supported Blender on macOS, Linux or Windows | Locked unit checks, exact-ZIP build/validation, isolated headless tests, GUI capture | A working desktop session is required for capture; inspect its PNG and record actual OS/Blender versions. Discovery is not compatibility proof. |
| Linux x64 without a display | Locked unit checks, build and isolated headless tests using an installed or explicitly fetched Blender | The official fetcher verifies archives. No GUI capture or input/rendering acceptance is established. |
| Sandbox without Blender | Locked unit checks, changed-file Ruff, knowledge and agent-skill checks; manifest-version output | Build, native and GUI checks cannot run. State those omissions in the PR so a reviewer or CI can supply the missing evidence. |

Build/install/test/capture commands always own fresh disposable profiles. The
[isolated command wrapper](../../CONTRIBUTING.md#isolated-blender-commands) also
owns a fresh profile for trusted local probes, without installing an extension.
None of these tools has a normal-profile mode. The unmanaged native-suite guard
exits with status 2 before importing Blender; use `make test-blender` for acceptance.
Capture artifacts use unique directories rather than overwriting a fixed PNG.
GUI probes never spend credits; capture requires a desktop session with the
necessary display access, which may be unavailable to a cloud agent.

The portable build/install tools also create fresh isolated profiles and scrub
inherited credentials and path overrides. For every direct Blender invocation outside these tools,
including probes, export an absolute disposable profile:
`export BLENDER_USER_RESOURCES="$PWD/.blender-profile"`.
Never install development builds into the user's normal profile.

Source builds run Blender's `extension validate` against `scenario/` before
staging dependencies or building an archive. The isolated runner records this
as `validate-source.log`, so malformed manifest metadata fails at a distinct
step on every Linux/Windows Blender CI version. A validation failure stops
packaging and installation and preserves its exit status and diagnostic logs.
The finished ZIP is still validated separately. When `tools/test_blender.py`
receives `--zip`, it validates that exact supplied artifact without checking
the source directory with this new preflight. The archive's extension id must
still match the checkout. `--no-build` uses the same validation path after selecting
only the exact `dist/ID-VERSION.zip` named by the checkout manifest; the copied
archive must have that id/version. Neither mode skips ZIP, licence, SDK bundle or
installed-byte checks. `--fresh` is a compatibility flag for the runner's existing
fresh-owned-profile behavior, not permission to clear an inherited profile.

The separate [native update fixture](../../tools/test_repository_update.py) tests
Blender's repository install and update mechanism with two synthetic extension
ZIPs. Run it with the selected binary:

```sh
uv run --locked --no-env-file python tools/test_repository_update.py \
  --blender /path/to/blender --expected-version 5.0.1
```

It validates and generates both repositories through the existing exact-inventory
helper, installs the first ZIP, and uses native refresh/update operators to load
the second version in the same Blender process while preserving enabled state.
Installed bytes must match each exact artifact. This tests the native mechanism;
it does not certify a published Scenario release, hosted repository, UI controls,
or production add-on upgrade behavior.

The fixture serves only its generated index and ZIP filenames on `127.0.0.1`.
Its disposable profile contains only that repository; Scenario credential variables,
Blender/Python path overrides and proxies are removed. Native network operations
use `--online-mode` for this loopback repository, without changing the normal
profile's online-access setting. This is configured loopback isolation, not a
sandbox policing arbitrary subprocess sockets. Do not add external destinations
to the fixture. The runner checks that the normal profile's file metadata is
unchanged and refuses artifact directories inside that profile.

The loopback server stops on success and failure. Successful profiles and
temporary files are removed; failed profiles remain with logs for diagnosis.
Reports, synthetic ZIPs and native logs stay under `.blender-profile/update-*`
(or `--artifacts`). The Linux and Windows baseline matrix runs this separate
fixture on Blender 5.0, 5.1 and 5.2 and preserves its evidence even on failure.

- `make build`: build and validate the extension ZIP; use
  `BLENDER_BUILD_ARGS="--repo"` to also generate a local extension repository.
- `make install`: build and install into a new isolated profile; use
  `BLENDER_INSTALL_ARGS="--launch"` to open it.
- `make test-blender`: build/validate/install an exact ZIP, then run the offline
  baseline in a new profile. No prior installation is needed. Logs and ZIP remain
  under `.blender-profile/run-*`; successful profiles are removed. Use
  `BLENDER_TEST_ARGS="--suite all"` for the full existing integration suite.
- `make gui-check`: build and capture an exact ZIP in a fresh offline GUI profile.
  Use `BLENDER_GUI_ARGS="--view composer --lane image --fixture form"` for a
  synthetic form, or `BLENDER_GUI_ARGS="--zip /path/to/scenario.zip"` to capture
  an existing artifact. A desktop display is required. Each capture keeps its
  PNG, ZIP, report and logs in a unique directory under `workdir/screenshots/`;
  successful disposable profiles are removed. Inspect the PNG before claiming
  visual acceptance. GUI probes never spend credits.
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
