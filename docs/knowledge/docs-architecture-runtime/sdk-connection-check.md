---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.sdk-connection-check",
  "title": "docs/architecture/runtime.md: SDK connection check",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "sdk-connection-check",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed Test connection worker ownership, the single one-model page read, cache preservation, shared pending checks, current-connection and current-request acceptance, background completion delivery without a GUI timer, account-strip status icons, credential-change and reset rejection, and the identity boundary against the current connection paths. Reviewed the adapter's fixed status text for SDK status errors: HTTP 401 and 403 ask to check the selected key and secret, a 403 names the Project ID only when that request carried the override, 429 asks for a later retry and other statuses keep the generic HTTP text, without response bodies, URLs or identifiers. Re-reviewed after the model-description retry change: its retry operator, recorded read failures, description validation and failed-read reporting leave the connection check paths unchanged. 3944 offline unit tests pass with the known SDK authentication xfail. Exact ZIP 9ad4511350c8cbc60077783c52888fe903fc14d0359bf7634d3b7491119d94f2 passes 1164 installed tests (2 Windows-only skips) on Blender 5.1.2 macOS arm64. An earlier isolated Blender 5.0.1 desktop check confirmed the pending hourglass while cached models remained loaded; this review did not repeat it. Blender 5.0.1/5.2.1 runs, desktop error/success and focus acceptance, live service responses, paid execution and account/project identity discovery are not claimed. Other guide topics retain their independent evidence limits.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "d2405048078890ff64037a359281ec1413cfd114e8bc599aa9bc29889f9638d3",
      "scenario/core/api/sdk_adapter.py": "5e81afa4ac8bd9e712e193037fae2bd2819f8d9a277089e7b622a038e910bba3",
      "scenario/core/jobs/manager.py": "f79ea01367faf949a139d7daaeb55ff47e58d86cc98fd58e5ed3c6bcfd6183ab",
      "scenario/blender/runtime.py": "43003d6a75ea5b11f2459ba56d39db94d43359a1cd1564765a10471d7979889e",
      "scenario/blender/operators.py": "41a8a513e4adec195e56794c7430078a95a46ddc1c48e2e682a24d2ff656512f",
      "scenario/blender/handlers.py": "699dba07a70d4b796f29e2e52799abb62d2ae7d0595b484c1f984f156cae1834",
      "scenario/blender/panels.py": "9d92e8074690c6174edd831af81bfd01e69197ca2f16e65d97f95afae63ed027",
      "scenario/prefs.py": "569ef8524cb0ba9e7d8f5b46582d4903b05d96a7cbc6cf1f2b3216be23c4ba96",
      "tests/unit/test_sdk_adapter.py": "c03504aba6fc4848abababab2245a5cb93cc6f64be685a4967e8b1c4cc67ff30",
      "tests/unit/test_sdk_connection.py": "035b6e016c8149b1102dd230c299d685ca4cc4a9c63226bc37c30ca689199f1a",
      "tests/blender/test_sdk_connection.py": "ff09606d34370b665a104983f99cb6b1aad9553a7c743e5c7080af85251b75c4",
      "tests/blender/run_all.py": "0c167da4d582bd9eda230638ec4259ba22357c857ffd240b58485cbdd07a26a1"
    }
  }
}
---

Evidence for [the canonical document](../../architecture/runtime.md).
