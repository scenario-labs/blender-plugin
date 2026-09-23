# Agent tools

Root [AGENTS.md](../../AGENTS.md) requires the canonical guides for every agent.
Claude's [core Python adapter](../../.claude/rules/core-python.md) and
[Blender adapter](../../.claude/rules/blender-glue.md) retain path-triggered reads.
They point to the same maintained guides and do not override root policy.

- `/download-artifacts <prnumber>`: collect the PR head's CI artifacts under
  ignored `workdir/`, preserve screenshot history and create a local review index.
- `/pr-summary`: update the current PR's summary/title from its actual diff and
  verified evidence; return a draft instead when requested.
- `/squash-message`: prepare and lint one squash message, align the PR title when
  needed, and copy it with `pbcopy` when available. It never commits or merges.

Private notes belong in ignored `.claude/CLAUDE.local.md` or `CLAUDE.local.md`.

## Shared skills and command validation

Keep canonical skills in regular `.agents/skills/<name>/SKILL.md` files, with valid
`name` and `description` frontmatter. Native skill directories link from
`.claude/skills/`. Command skills use `metadata.claude-command` or
`metadata.cursor-command` to retain existing command names; compatibility paths
are relative symlinks directly to the canonical `SKILL.md`. Edit the original in
`.agents/skills/` (plural), never a separate command copy. Keep Claude argument
hints and invocation guards in the canonical frontmatter; keep Codex picker and
invocation policy in the adjacent `agents/openai.yaml`. No forwarding wrapper is
needed.

| Codex skill | Claude command | Purpose |
| --- | --- | --- |
| `$blender-download-artifacts <prnumber>` | `/download-artifacts <prnumber>` | Collect current PR artifacts; explicit invocation only |
| `$blender-pr-summary` | `/pr-summary` | Refresh the current PR description |
| `$blender-squash-message` | `/squash-message` | Prepare the current PR squash message |

Each command includes a Codex picker description and starting prompt in
`agents/openai.yaml`. Keep these consistent with its canonical instructions.

Run `uv run --no-project --python 3.12 scripts/agents/validate-skills.py --sync` after adding or
renaming a skill. Without `--sync`, the same command checks all skills with the
pinned Agent Skills reference validator and verifies the rulebook and command
links without writing. Registered local maintainer commands additionally allow
`argument-hint` and `disable-model-invocation`, checked against their command
contracts; native skills retain strict reference validation. CI runs this check
on every pull request.

CI also checks direct command links, argument hints, Codex picker metadata,
explicit invocation guards on both agents, and the Codex instruction byte limit.
Run the regression suite with
`uv run --no-project --python 3.12 scripts/agents/validate-skills.py --test`.
