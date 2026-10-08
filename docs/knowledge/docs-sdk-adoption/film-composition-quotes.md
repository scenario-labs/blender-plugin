---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.film-composition-quotes",
  "title": "Verified composition quote and dispatch guards",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "film-composition-quotes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected owner-issued media tickets, source checks around schema/estimate/preparation/dispatch, original-origin delivery, exact decimal cost and ordinary durable single-submission behavior. Synthetic SDK tests and installed session tests establish these local boundaries; no live provider, native/MCP review controls, final assembly/export or release acceptance. Source checks are current-record observations, not a transaction locking all source records or remote assets for the whole request. Guard objects are session-local, not restored spend authority. Only this quote topic was reviewed.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "11eda828ba97ac1aefa860a2b7d23cfe26f97d038e5bcdefbea1d1507b34b129",
      "scenario/core/jobs/film_finishing.py": "ee7d6ea086f427120976b6ae34be9189adae97b841f0790903ae619f972341fc",
      "scenario/core/jobs/film_media.py": "a3eb437f59768cd6abd7eb7ca9efb7300607fb5c0ee0ea19cf49cf355148e1a0",
      "scenario/core/jobs/workers.py": "27911d68f01d8e695986a3681dfad6780aaf50cd06b369749e88d8cf250f2d67",
      "scenario/blender/job_session.py": "1e306d0ccf0ead6229ea33dc2da77014fbaae77ec4a8d399c2a6b38cb7f00bbf",
      "scenario/core/api/sdk_adapter.py": "6cc3758eebf05f066a0aa11ed4d5c6ec96fb87b72f02f3d609cfdd97b88b044e",
      "scenario/core/jobs/store.py": "e183f93bbe72bbaf6c204238e4e46dba0b37cf9c4989256327b87a7e02612ec3",
      "tests/unit/test_film_composition_quotes.py": "7418e06fd18fb5fb6297738ec8607ff80f43002d98edcbb075f5c841591b7d05",
      "tests/unit/test_film_media.py": "5051e2fadcdedb9eefb38686bb4b8fd85a21d967816103cba23b4634319af45a",
      "tests/unit/test_scenario_sdk_contract.py": "3b2b866d7bf0c816c3108b0ad9f6322e95cdc9808627c015917f591250d5371c",
      "tests/blender/test_film_finishing.py": "dd9a40367ab462c4709d4c56ea4134c5cc3ae29016ed9b61a0fe8241c0ea254f"
    }
  }
}
---

Source evidence for [the canonical guide](../../SDK_ADOPTION.md).
