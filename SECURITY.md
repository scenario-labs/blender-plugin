# Security Policy

## Reporting a vulnerability

Do not report security vulnerabilities through public GitHub issues or pull
requests. Public reports can expose other users before a fix is available, and
copies may remain accessible after deletion.

Report privately through any of these channels:

- [Open a private vulnerability report](https://github.com/scenario-labs/blender-plugin/security/advisories/new)
  from this repository's Security tab.
- Email [support@scenario.com](mailto:support@scenario.com) with "security" in the subject.
- Use in-app support at [app.scenario.com](https://app.scenario.com).

Include the affected surface (Blender extension, local MCP server or Scenario
platform), Blender and extension versions, reproduction steps and the impact you
observe. The extension version is shown in Preferences > Add-ons > Scenario and
in `scenario/blender_manifest.toml`. Use synthetic credentials and minimal sample
files where possible. Scenario support routes reports to the appropriate team
and follows up through the same private channel.

## Scope

This repository ships Scenario for Blender. It uses Scenario API credentials,
communicates with `api.cloud.scenario.com`, saves generated files and imports
media into Blender, and provides a local MCP server. Relevant reports include:

- Unexpected exposure of keys, secrets or signed URLs through preferences, logs,
  errors, files or network requests, including credential-source selection involving
  `SCENARIO_API_KEY`, `SCENARIO_API_SECRET` and saved Blender preferences.
- Local MCP tool calls accepted without the configured bearer token, or a listener
  exposed beyond loopback. Its default address is `http://127.0.0.1:9876/mcp`.
- MCP `execute_python` running while Allow connected agents to run Python is off
  in Preferences. It is disabled by default; enabling it permits Python execution
  with the Blender user's privileges. The Python guard is not a security sandbox.
- Unsafe downloads or imports of images, video, audio, glTF/GLB, FBX, OBJ, SPZ, PLY
  or other generated content, and cross-scene or cross-account result application.
- Headless command mode, the local stdio shim, helper scripts,
  bundled dependencies and the repository's CI or release supply chain.

Platform vulnerabilities involving `app.scenario.com`, `api.cloud.scenario.com`
or the remote server at `mcp.scenario.com` use the same private channels above,
not this repository's public issue tracker. This scope describes reportable
problems; it does not certify the current implementation or its pending fixes.

The repository's [OpenSSF Scorecard result](https://scorecard.dev/viewer/?uri=github.com/scenario-labs/blender-plugin)
is published by [Scorecard CI](.github/workflows/scorecard.yml) after pushes to
`main` and weekly. A lower score is a maintainer triage signal, not a release
blocker. See the [maintenance procedure](docs/development/contributions.md#scorecard-triage)
for publication checks and limitations; the badge needs a successful run on `main`.

## Supported versions

Security fixes target the [latest release](https://github.com/scenario-labs/blender-plugin/releases).
Where practical, check whether the problem still occurs in that release. Report
suspected vulnerabilities promptly even if you cannot update or reproduce them
on the latest version. There is no separate standing support branch for older
extension releases.

## Secrets in issues and pull requests

API keys and secrets, local MCP bearer tokens and signed asset URLs are
credentials. Never commit them or paste them into public issues or pull requests.
Check screenshots, copied connection snippets, logs and sample files before
sharing them. If a secret is already exposed, report it privately instead of
pointing to it in a public issue, and revoke or rotate credentials you control.
