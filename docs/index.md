# Scenario for Blender documentation

Start with the [repository overview](../README.md), [user guide](USER_GUIDE.md) and
[known limitations](KNOWN_LIMITATIONS.md) before relying on an experimental
workflow. The [changelog](../CHANGELOG.md) records releases. Documentation of a
new primitive does not mean it is wired into the user interface or local MCP.

For questions, bugs or account help, see [Support](../SUPPORT.md).

## Architecture and implementation

- [Local MCP tools, setup and security](MCP.md)

- [Privacy and data handling](PRIVACY.md)
- [Runtime map and integration status](architecture/runtime.md)
- [Blender boundaries and scene application](architecture/blender.md)
- [SDK adoption and operation contracts](SDK_ADOPTION.md)
- [Dependency bundle and supported artifacts](SDK_BUNDLE.md)
- [Durable job storage](JOB_STORAGE.md)
- [Job coordinator, workers and cancellation](JOB_COORDINATOR.md)
- [Blender job context and stale-result guards](BLENDER_JOB_CONTEXT.md)
- [Signed result transfers](RESULT_TRANSFERS.md)
- [Multipart upload lifecycle](SDK_UPLOADS.md)
- [Reversible mesh application](MESH_APPLICATION.md)
- [Panoramic World application](WORLD_APPLICATION.md)
- [Source adoption decisions](STUDIO_ADOPTION.md)

## Development and contributions

- [Private vulnerability reporting and security scope](../SECURITY.md)
- [Trademarks and official builds](../TRADEMARKS.md)
- [Contributor setup and environment](../CONTRIBUTING.md)
- [Canonical agent instructions](../AGENTS.md)
- [Python style and linting](PYTHON_STYLE.md)
- [Model schema audit and offline reports](MODEL_PAYLOAD_AUDIT.md)
- [UI style and native interaction](UI_STYLE.md)
- [Validation and local commands](development/validation.md)
- [Recorded fixture inventory and offline hygiene](../tests/fixtures/README.md)
- [Commits, PRs and review follow-up](development/contributions.md)
- [Agent skills and command adapters](development/agents.md)
- [Release procedure](RELEASING.md)

## Maintenance and historical evidence

- [Repository baseline and pending administration](MAINTAINERS.md)
- [Knowledge checks and review procedure](maintenance/knowledge.md)
- [API-key release plan](maintenance/release-plan.md)
- [Issue disposition and limitations audit](maintenance/backlog.md)
- [Evidence discovery configuration](knowledge.json)
- [Topic evidence concepts](knowledge/)

The topic records describe source inspection and fingerprints, not human approval or
live service acceptance. It includes inherited guides with explicit coverage
limits; their presence here does not certify every historical claim.
