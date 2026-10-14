# Maintaining repository knowledge

[The index](../index.md) is the navigation entry point.
[knowledge.json](../knowledge.json) tells the checker where evidence lives.
Each canonical Markdown document has one evidence record in
[docs/knowledge/](../knowledge/). That covers every document under `docs/`, the
root README, AGENTS, CONTRIBUTING and Claude path adapters. Guides remain the
policy authority; records only say what a guide was last checked against.

## Who edits what

| Change | Edit |
| --- | --- |
| Feature or fix | The prose your change makes wrong, kept short. Never a record, unless the checker fails. |
| New canonical document | The document, a link to it from a reachable guide, and its new record. |
| Renamed or deleted source | Nothing: the release refresh updates the source lists. |
| Release refresh | Drifted documents and their records, in one PR per version. |

Feature PRs do not refresh evidence. Concurrent PRs then rarely touch the same
lines, and the drift each PR causes stays visible until the refresh reviews it.
Test runs, platforms and review notes go in the PR body, not in docs or records.

## Evidence records

A record is an [Open Knowledge Format 0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/SPEC.md)
concept: Markdown with JSON frontmatter, a YAML 1.2 subset the checker reads with
Python's standard library. Its file name is its `id`, for example
`docs/knowledge/docs-ui-style.md`. The body links back to the document.

| Field | Meaning |
| --- | --- |
| `evidence.path` | The canonical document this record covers. |
| `evidence.coverage` | One of the classifications below. |
| `evidence.reviewed_at` | UTC date of the last review, `YYYY-MM-DD`. |
| `evidence.reviewed_revision` | Full SHA of the main commit the review checked. |
| `evidence.limits` | At most 60 words on what the review did not establish. |
| `evidence.sources` | Sorted repository paths whose changes can make the document wrong. |

Coverage classifications:

- `source-reviewed`: implementation paths were inspected for the stated claims.
- `policy`: maintained normative guidance; it does not prove implementation.
- `navigation`: an entry point or maintenance procedure.
- `inherited`: indexed without a full claim-by-claim review.
- `historical`: superseded design or recorded evidence, not current instructions.

`limits` states current boundaries, such as "no live Scenario call" or "macOS
only". It is not a log: do not add dated re-check notes. Git and PR bodies keep
history. Neither `reviewed_at` nor a passing check implies human approval; do not
invent OKF `verified` attestations.

## Checks

From the repository root, run:

```sh
make knowledge
git fetch origin main
uv run --locked --no-env-file python tools/check_knowledge.py --base origin/main --json
uv run --locked --no-env-file python -m pytest tests/unit/test_knowledge.py
```

In a fork clone, fetch the remote that tracks `scenario-labs/blender-plugin`
(commonly `upstream`) and pass `--base upstream/main`. The fetch is the only
online step. [The checker](../../tools/check_knowledge.py) uses Git and Python's
standard library; it follows no external URLs, executes no examples and calls no
model or service. [CI](../../.github/workflows/knowledge.yml) runs it with
`--base origin/main` on PRs and main and prints drift in the job summary.

Errors fail the check: malformed records or registry, unknown evidence fields,
`limits` over 60 words, unsorted or untracked sources, undocumented or
duplicated documents, broken local links or Markdown fragments, root-relative
links, and documents unreachable from the index. Link parsing covers inline links,
images and reference definitions; fenced examples and inline code are ignored.
HTML links and external URLs are outside this check (#47).

With `--base REF`, every `reviewed_revision` must be reachable from that ref, so
an unmerged or pre-squash PR commit fails even if it exists locally. The report
also lists the files the branch changes since its merge base and the documents
whose sources those files are.

Drift is a warning, one per document: the sources Git reports as changed since
`reviewed_revision`, including committed, staged, unstaged and removed files. It
asks for a review; it is not proof that the document is wrong.

## Release refresh

Once a version's scope is settled, one agent or maintainer refreshes the drifted
documents on a branch from current main and opens a single PR. Only one refresh
runs at a time, so it does not conflict with itself. Agents run it with
`/knowledge-refresh` (Codex: `$blender-knowledge-refresh`).

1. Run the checker with `--base origin/main --json` and take its `drift` list.
2. For each drifted document, read `git diff <reviewed_revision>..origin/main --`
   on its drifted sources. Correct the prose that the changes made wrong by
   replacing or deleting it. Add no dates, test runs or review remarks. A
   refreshed document should not grow unless new behavior needs the lines.
3. Update that record: prune or add sources, set `reviewed_revision` to the main
   commit you reviewed and `reviewed_at` to today's UTC date, and rewrite
   `limits` as current boundaries. Narrow `coverage` only after reviewing the
   claims it covers.
4. Leave a document's record unchanged when you did not review it; its drift
   stays visible for the next refresh.
5. Run the checks above and list the documents left drifted in the PR body.

Get the UTC date with
`uv run --locked --no-env-file python -c "from datetime import datetime, UTC; print(datetime.now(UTC).date())"`.
Do not move `reviewed_revision` to silence a warning without reading the change.

## Instructions and future automation

[AGENTS.md](../../AGENTS.md) retains repository-wide requirements and explicit
read triggers. Detailed [validation](../development/validation.md),
[contribution](../development/contributions.md) and [agent tooling](../development/agents.md)
guides are canonical. Claude path adapters route to these same guides; their
presence does not create a second policy authority.

Scheduled model-generated refreshes are deferred. Any future automation needs a
single reviewable PR, preserved human edits, rejection/pause behavior and
explicit per-run and monthly spending limits before enabling paid execution.
