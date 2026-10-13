---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.studio-source",
  "title": "Selected Studio source and its service client",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "studio-source",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "34ce22e8a4b037312334d98fbec6641da45a9a45",
    "limits": "Read on 2026-10-13 from Studio 0.2.0 at 204c847ad6f999e1050070a35e58af666b28ff9c: src/scenario_studio/client.py still implements a remote-MCP client, now with usage, recommend and assets_get_bulk calls, a raw public-workflow HTTP request and a direct thumbnail download; its read retries and download resume live in that client. Checked against the canonical shared adapter, which configures the SDK client with max_retries=0 for every call. No Studio code was executed or imported.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "0add4688710b00326fc31381d028e42cd9b5415f84bd168f45b5a8434a48aa19"
    }
  }
}
---

Source evidence for [the canonical guide](../../SDK_ADOPTION.md).
