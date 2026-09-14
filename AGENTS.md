# Scenario for Blender: Codex instructions

## Shared repository conventions

Before working in this repository, read and follow
[`.claude/CLAUDE.md`](.claude/CLAUDE.md). It is the canonical source for shared
repository conventions, architecture, validation and contribution requirements.
Keep shared rules there; this file adds Codex-specific guidance.

## Codex commit attribution

For Codex-assisted commits and prepared squash messages, include a co-author
trailer naming the model and, when verified, the reasoning effort and speed tier:
`Co-authored-by: Codex <model> <effort> <tier> <noreply@openai.com>`.
For example: `Co-authored-by: Codex gpt-6-astra low fast <noreply@openai.com>`.
Use the actual settings for the contributing session, not repository defaults
or the example above. Omit unknown fields rather than guessing; if the model
is unavailable, use `Co-authored-by: Codex <noreply@openai.com>`. Preserve the
human author and existing contributor trailers. Carry these trailers into the
final squash message so attribution survives the repository's squash workflow.
