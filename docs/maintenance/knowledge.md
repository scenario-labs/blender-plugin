# Maintaining repository knowledge

[The index](../index.md) is the navigation entry point.
[knowledge.json](../knowledge.json) is the evidence registry for every Markdown
document under `docs/`, plus root README, AGENTS, CONTRIBUTING and Claude path adapters. Existing
technical guides keep their paths; avoid a second copy of their policy text.

## Offline checks

From the repository root, run:

```sh
make knowledge
uv run --locked --no-env-file python tools/check_knowledge.py --base origin/main --json
uv run --locked --no-env-file python -m pytest tests/unit/test_knowledge.py
```

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

With `--base REF`, the registry's `base_revision` must also be reachable from
that comparison commit. A missing ref or an unmerged/pre-squash PR commit fails,
even when the latter still exists in the local Git object cache. This prevents
metadata that passes in an author's checkout but breaks in a fresh clone after
a squash merge. Without `--base`, the existing standalone check only requires
the recorded commit to exist locally; `make knowledge` retains that behavior.

## Evidence fields

The registry has version, index, base_revision and documents fields. Each document
records its path, coverage, reviewed_at date, limits, and a nonempty map of exact
repository-relative source paths to SHA256 fingerprints.

- `source-reviewed`: implementation paths were inspected for the stated claims.
- `policy`: maintained normative guidance; it does not prove implementation.
- `navigation`: an entry point or maintenance procedure.
- `inherited`: existing content indexed without a fresh claim-by-claim audit.
- `historical`: superseded design or recorded evidence, not current instructions.

`base_revision` identifies the durable main commit used as the base for this
review batch. For stacked PRs, keep a main ancestor here and record the exact
temporary parent in the PR description; a parent's branch SHA can disappear
after its squash merge. Fingerprints
identify the exact local source contents inspected, including changes proposed
in the same PR; do not claim every fingerprint is the content at that base commit.
The merged PR preserves the review diff. `reviewed_at` records this evidence pass,
not human approval. Inherited documents have a date for registry intake, with
their lack of fresh factual verification stated in `limits`.

Source lists are deliberately explicit. Cover relevant tests and entry points,
not just the implementation's filename. Adding a source outside the list cannot
automatically be detected as semantic drift. Review the list when responsibilities
move or expand. Fingerprints detect byte changes, not truth or live behavior.

## Review procedure

1. Inspect the affected source, tests, document and open issue acceptance. Keep
   implemented behavior separate from planned integration and live proof.
2. Correct the document or explain why it remains accurate. Preserve ownership,
   source attribution, unknowns and coverage limits; do not infer human approval.
3. Update only the reviewed entry's source list, SHA256 values and review date.
   A hash can be computed with `hashlib.sha256(Path(path).read_bytes()).hexdigest()`.
   There is intentionally no bulk refresh command that could erase warnings
   without review. Update the batch base only when recording a new review pass.
4. Link new Markdown documents from the index or an already reachable guide,
   register their evidence and run the checks above. Keep private notes ignored.
5. Report remaining warnings and incomplete issue scope in the PR. A green check
   certifies this structural subset; it cannot certify prose, product readiness,
   live API behavior or native Blender support.

## Instructions and future automation

[AGENTS.md](../../AGENTS.md) retains repository-wide requirements and explicit
read triggers. Detailed [validation](../development/validation.md),
[contribution](../development/contributions.md) and [agent tooling](../development/agents.md)
guides are canonical. Claude path adapters route to these same guides; their
presence does not create a second policy authority.

Scheduled model-generated updates are deferred. Any future automation needs a
single reviewable proposal, preserved human edits, rejection/pause behavior and
explicit per-run and monthly spending limits before enabling paid execution.
