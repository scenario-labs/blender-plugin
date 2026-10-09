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
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed Test connection worker ownership, the single one-model page read, cache preservation, shared pending checks, current-connection and current-request acceptance, background completion delivery without a GUI timer, account-strip status icons, credential-change and reset rejection, and the identity boundary against the current connection paths. Reviewed the adapter's fixed status text for SDK status errors: HTTP 401 and 403 ask to check the selected key and secret, a 403 names the Project ID only when that request carried the override, 429 asks for a later retry and other statuses keep the generic HTTP text, except that a model record read through SDKAdapter.model reports HTTP 403 or 404 as not available to the selected credentials or project (#357), without response bodies, URLs or identifiers. Re-reviewed after the model-description retry change: its retry operator, recorded read failures, description validation and failed-read reporting leave the connection check paths unchanged. 3944 offline unit tests pass with the known SDK authentication xfail. Exact ZIP 9ad4511350c8cbc60077783c52888fe903fc14d0359bf7634d3b7491119d94f2 passes 1164 installed tests (2 Windows-only skips) on Blender 5.1.2 macOS arm64. Re-reviewed on 33d00b05 with the workflow decision rebase: the connection check still reads one public model page through SDKAdapter.model_page, which never raises AdapterUnavailable; status failures now raise the AdapterStatusError subclass with the same text, which SDKCatalog maps like any AdapterError; a request sent with the SDK omit sentinel never names the Project ID; the bulk-summary reads in sdk_catalog.py and the prepared-job cancellation view in runtime.py leave the connection check paths unchanged. 4458 offline unit tests pass with the same xfail. Exact ZIP 54d6c6e016a426cac31e094236c3c8e9483089c0416183b7fb8255c276bc9423 passes 1204 installed tests (2 Windows-only skips) on Blender 5.1.2 macOS arm64. An earlier isolated Blender 5.0.1 desktop check confirmed the pending hourglass while cached models remained loaded; this review did not repeat it. Blender 5.0.1/5.2.1 runs, desktop error/success and focus acceptance, live service responses, paid execution and account/project identity discovery are not claimed. Other guide topics retain their independent evidence limits.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "scenario/core/api/sdk_adapter.py": "82d37a4f38b72726ca0060ee0cf66e769cec758f96a166aeeed92580d3fe0a08",
      "scenario/core/jobs/manager.py": "f79ea01367faf949a139d7daaeb55ff47e58d86cc98fd58e5ed3c6bcfd6183ab",
      "scenario/blender/runtime.py": "fb83ceaa622cbbfbea25210d2bb8d480231510d11712f58df34f45f41c13cf59",
      "scenario/blender/operators.py": "41a8a513e4adec195e56794c7430078a95a46ddc1c48e2e682a24d2ff656512f",
      "scenario/blender/handlers.py": "699dba07a70d4b796f29e2e52799abb62d2ae7d0595b484c1f984f156cae1834",
      "scenario/blender/panels.py": "9d92e8074690c6174edd831af81bfd01e69197ca2f16e65d97f95afae63ed027",
      "scenario/prefs.py": "569ef8524cb0ba9e7d8f5b46582d4903b05d96a7cbc6cf1f2b3216be23c4ba96",
      "tests/unit/test_sdk_adapter.py": "37e9dcb823c8d199794cddc19c809fbceff6c99eae2823a18b401ecd5df9fbbf",
      "tests/unit/test_sdk_connection.py": "035b6e016c8149b1102dd230c299d685ca4cc4a9c63226bc37c30ca689199f1a",
      "tests/blender/test_sdk_connection.py": "ff09606d34370b665a104983f99cb6b1aad9553a7c743e5c7080af85251b75c4",
      "tests/blender/run_all.py": "0c167da4d582bd9eda230638ec4259ba22357c857ffd240b58485cbdd07a26a1"
    }
  }
}
---

Evidence for [the canonical document](../../architecture/runtime.md).
