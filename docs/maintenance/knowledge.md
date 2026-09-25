# Maintaining repository knowledge

[The index](../index.md) is the navigation entry point.
[knowledge.json](../knowledge.json) is a small discovery configuration. Evidence
lives in [topic concepts](../knowledge/), separate from canonical guide prose.
Every Markdown document under `docs/`, plus root README, AGENTS, CONTRIBUTING and
Claude path adapters, needs evidence. Concepts themselves do not need recursive
evidence records. Existing guides keep their paths and remain the policy authority.

## Offline checks

From the repository root, run:

```sh
make knowledge
git fetch origin main
uv run --locked --no-env-file python tools/check_knowledge.py --base origin/main --json
uv run --locked --no-env-file python -m pytest tests/unit/test_knowledge.py
```

The example assumes `origin` is the canonical `scenario-labs/blender-plugin`
repository. Check `git remote -v` first. In a fork clone, refresh the remote that
tracks the canonical repository (commonly `git fetch upstream main`) and pass
`--base upstream/main` instead. The checker does not fetch, identify an authoritative
remote or infer freshness: you select the comparison ref. A stale fork or local
ref can reject a valid newer review base; refresh/select the canonical main ref
before changing registry evidence. The fetch is an explicit online preparation
step, separate from the offline checks.

[The checker](../../tools/check_knowledge.py) uses Python's standard library and
Git. It reads tracked and nonignored proposed files, follows no external URLs,
executes no documentation examples and performs no model or service calls.
[CI](../../.github/workflows/knowledge.yml) runs structure checks with
`--base origin/main` and regression tests on PRs and main. The existing full-history
checkout supplies that comparison ref, including in fork PRs; the checker needs
no network calls, credentials or write permissions. It prints freshness warnings
in the job summary.

Structural errors fail: malformed metadata, absent sources, files outside the
repository, ignored file links, unregistered documents, broken local links or
Markdown fragments, and documents unreachable from the index. Link parsing
supports ordinary inline Markdown links/images and reference definitions,
including angle-bracket destinations with spaces. Local links must be relative
to their document; leading-slash paths are rejected with a diagnostic naming the
link. Undefined-reference checks apply to standalone bracket pairs, excluding
attached indexing notation such as `config[env][key]` and escaped opening brackets.
Fenced examples and inline code are ignored. It is not a full HTML or CommonMark renderer; HTML links and
external URL redirects/availability remain outside this check (#47).

Changed source bytes and reviews older than 45 days produce warnings. A warning
is a request to inspect the affected document, not proof it is wrong. Missing
sources fail so deletion or renaming cannot silently retire evidence. The
optional impact report compares against Git's merge base and includes committed,
staged, unstaged, deleted and nonignored new files. It is a file-level signal,
not a dependency analysis of all runtime consumers.

With `--base REF`, each topic's `base_revision` must also be reachable from
that comparison commit. A missing ref or an unmerged/pre-squash PR commit fails,
even when the latter still exists in the local Git object cache. This prevents
metadata that passes in an author's checkout but breaks in a fresh clone after
a squash merge. Without `--base`, the existing standalone check only requires
the recorded commit to exist locally; `make knowledge` retains that behavior.

## Topic concepts and OKF

The repository uses [Open Knowledge Format 0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/SPEC.md)
concepts: Markdown with frontmatter, a `type`, and optional descriptive fields.
Our local profile serializes the frontmatter as JSON, a YAML 1.2 subset, so the
checker needs only Python's standard library. General YAML syntax is not accepted
by this checker. The stricter evidence and link rules below are repository
requirements, not guarantees supplied by OKF.

Version 2 of `knowledge.json` contains only `version`, `index` and
`records: {"root": "docs/knowledge", "format": "okf-json"}`. The checker discovers
tracked and nonignored `.md` records beneath that directory. There is no central
list to append to, global review date or batch revision to update. The checker
also understands the legacy version 1 registry during branch migration; mixing
legacy document ownership with topic records fails instead of silently choosing
one source of truth.

Keep stable, descriptive paths such as
`docs/knowledge/contributing/weekly-platform-ci.md`. They represent current
knowledge about a topic, not a PR, session or review-history event. Git retains
history. The record body links back to its canonical document.

Each record has `type: "Evidence"`, a unique `id`, and an `evidence` object:

| Field | Meaning |
| --- | --- |
| `path` | Canonical Markdown document supported by this record. |
| `scope` | Stable topic name, unique within that document. |
| `coverage` | One of the classifications below. |
| `reviewed_at` | Actual evidence review or inherited intake date in UTC, `YYYY-MM-DD`. |
| `base_revision` | Full SHA of the durable main commit used for the review. |
| `limits` | Explicit claim, inspection and acceptance boundaries. |
| `sources` | Nonempty map of exact repository-relative source paths to SHA256 fingerprints. |

Several topics may support the same document. For example, weekly platform CI,
local hooks and handbook rendering have separate evidence for CONTRIBUTING.
Updating the handbook topic must not refresh the CI topic's date or fingerprints.
Overlapping sources are permitted when both topics depend on them; their drift
remains visible independently. Duplicate IDs and duplicate document/topic pairs
are errors.

Coverage classifications remain:

- `source-reviewed`: implementation paths were inspected for the stated claims.
- `policy`: maintained normative guidance; it does not prove implementation.
- `navigation`: an entry point or maintenance procedure.
- `inherited`: content indexed without a fresh claim-by-claim audit.
- `historical`: superseded design or recorded evidence, not current instructions.

For stacked PRs, keep a main ancestor as `base_revision` and record the exact
temporary parent in the PR description. A parent's branch SHA can disappear after
its squash merge. Fingerprints identify the exact local source contents inspected,
including proposed changes; they need not match bytes at the review base.
Neither `reviewed_at` nor a passing structural check implies human approval.
Do not invent OKF `verified` attestations.

Use the UTC calendar date when recording a new review. The checker uses UTC for
both future-date rejection and the 45-day warning, so local and hosted checks
agree around midnight. For example, obtain the date with
`uv run --locked --no-env-file python -c "from datetime import datetime, UTC; print(datetime.now(UTC).date())"`.
Your local calendar may be a day ahead or behind. Do not advance an existing
review date merely to clear a warning or while moving evidence between topics.

Source lists are explicit. Cover relevant tests and entry points, not just an
implementation filename. Newly relevant sources cannot be discovered from byte
hashes alone. Review ownership when responsibilities move or expand.

## Review procedure

1. Inspect the affected source, tests, document and current issue acceptance.
   Separate implemented behavior from planned integration and live proof.
2. Find its topic record by `evidence.path`, `scope` or a source path. Correct the
   canonical prose or explain why it remains accurate. Preserve limitations,
   attribution and unknowns.
3. Update only that topic's sources, SHA256 values, limits and actual review date.
   Compute a hash with `hashlib.sha256(Path(path).read_bytes()).hexdigest()`.
   Add a stable topic when a new independent responsibility appears; do not append
   unrelated review paragraphs to an umbrella record. Narrow inherited limits
   only after reviewing the claims they cover. A rebase alone is not a review.
4. Link new canonical Markdown documents from the index or a reachable guide and
   add their evidence concepts. Discovery needs no central registration edit.
5. Run the checks above and report remaining warnings and incomplete issue scope.
   Keep generated JSON reports in ignored `workdir/` or CI artifacts. Do not commit
   a regenerated aggregate registry or use a union/ours/theirs merge driver to
   hide conflicting evidence.

There is intentionally no bulk hash-refresh command. Source drift, stale reviews
and true simultaneous changes to the same topic still require inspection.

## Migration and open branches

The initial split preserves the existing coverage, review dates, source digests
and document-wide limitations. Source-family grouping does not certify a new
claim-by-claim review. An imported topic can retain limitations about neighboring
subjects until an actual scoped review narrows them. The mechanical migration
must preserve every document/source fingerprint and must not erase stale warnings.

For an older branch, compare its legacy registry with its original merge base.
Transfer only its evidence changes into the matching topic records. Preserve new
source keys and coverage limits; reconcile competing edits to the same source
against the resulting implementation. Leave unrelated topics alone. Keep existing
stack dependencies and durable-main bases. Run the checker against the resulting
checkout, rather than replacing the entire registry with either side of a merge.

## Instructions and future automation

[AGENTS.md](../../AGENTS.md) retains repository-wide requirements and explicit
read triggers. Detailed [validation](../development/validation.md),
[contribution](../development/contributions.md) and [agent tooling](../development/agents.md)
guides are canonical. Claude path adapters route to these same guides; their
presence does not create a second policy authority.

Scheduled model-generated updates are deferred. Any future automation needs a
single reviewable proposal, preserved human edits, rejection/pause behavior and
explicit per-run and monthly spending limits before enabling paid execution.
