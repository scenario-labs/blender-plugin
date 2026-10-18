---
{
  "type": "Evidence",
  "id": "docs-development-agents",
  "title": "docs/development/agents.md evidence",
  "evidence": {
    "path": "docs/development/agents.md",
    "coverage": "policy",
    "reviewed_at": "2026-10-18",
    "reviewed_revision": "04c30c3b7815ff8983a59c0e37a05608db23455e",
    "limits": "Commands, links, settings and validator options were checked against the skill files, project settings, MCP client templates, lock file and validator source. The validator was not run, and Codex or Claude command invocation was not exercised.",
    "sources": [
      ".agents/skills/blender-download-artifacts/SKILL.md",
      ".agents/skills/blender-download-artifacts/agents/openai.yaml",
      ".agents/skills/blender-knowledge-refresh/SKILL.md",
      ".agents/skills/blender-knowledge-refresh/agents/openai.yaml",
      ".claude/settings.json",
      ".codex/config.toml",
      ".github/workflows/agent-skills.yml",
      ".mcp.json",
      "CONTRIBUTING.md",
      "scripts/agents/test_validate_skills.py",
      "scripts/agents/validate-skills.py",
      "skills-lock.json",
      "tests/unit/test_agent_settings.py"
    ]
  }
}
---

Evidence for [the canonical document](../development/agents.md).
