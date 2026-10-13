---
{
  "type": "Evidence",
  "id": "docs-user-guide.native-library-view",
  "title": "Native scoped Library browsing and model reference confirmation",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "native-library-view",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "Reviewed on 2026-10-13 against the rewritten Browse Library assets section. Checked in code: Studio has a Library page; drawing starts no read, so assets list only after Refresh, and changed filters need another Refresh; Public assets reads the public catalog, Search runs a text search and Collection ID browses that collection, and Search with a Collection ID is refused; Use as reference opens a confirmation naming the asset, scene and destination and adds the asset only after OK, to a matching model input of the selected Create form or, with Reference destination set to Workflow, to a matching input of the loaded workflow; an occupied single input or a full array is not offered, arrays append and nothing is replaced; changing credentials or the Project ID retires the Library, and loading a file deactivates its session, so the page asks for Refresh again. Library rows show name, file type, tags and collections, without thumbnails; the guide makes no Library thumbnail claim. Sources read: library_view, workflow_references choices and attach, reference_form destination and scope keys, job_session asset reads and file-load deactivation, runtime retirement, studio pages, registry, asset_summary and the local MCP asset-read wrapper that tests/blender/test_asset_library.py drives. The workflow-side append and clear rules are evidenced by the workflow-library-references topic. Offline unit tests tests/unit/test_asset_library.py, test_library_organization.py, test_asset_organization.py and test_sdk_adapter_organization.py passed (440). The native tests in tests/blender/test_library_view.py, test_asset_library.py and test_studio_view.py were read, not run; earlier installed-ZIP results predate these sources and are not relied on. Not verified here: installed runs of this code on Blender 5.0, 5.1 or 5.2, native desktop input, focus, DPI and other operating systems (#66), and live service behaviour. No live calls or spending.",
    "sources": {
      "docs/USER_GUIDE.md": "d81c4fbc7ccd6fd05b987dfc9a77f191ad567cc0486b2f9983b755402bad526b",
      "scenario/blender/library_view.py": "b6a0757506308b0a106a914389d6a25fad9533bc132018e5b904f183c4633737",
      "scenario/blender/job_session.py": "b20ae0be8fbec16510d6750fa50757f7830ebf937f65649e186c16ee9068fb28",
      "scenario/blender/reference_form.py": "3b7433c9e3a9243f08a9fa031cf7bafddcdaa03ff5f2663455aa209f30ef5138",
      "scenario/blender/workflow_references.py": "64eb574c5c8c377dcfbe91c91f0dab27ffcbb52445f68628c460aa0274ff5535",
      "scenario/blender/runtime.py": "c8303eead552a5de421c69c56cb754c2d463f117909b46273c791d46275eb707",
      "scenario/blender/registry.py": "c3a880832b4cf47ce530ecea582a5c73e53c8f346d5a6521b7c023bab31cd9e3",
      "scenario/blender/studio.py": "41e0e0305bb47e3c82809fdfcddf34a89406198f2745e0009cfde697575b217c",
      "scenario/core/api/library.py": "4b2b71807f983f6ea9d2cde1d54f969de7f99d1f3fbd5a5cf29459704861d4ca",
      "scenario/mcp/tools_scenario.py": "f9e4447cc3b1a1cae05f5fd3148940f25f39c3bbfbbc62b876ab524b5af0d83f",
      "tests/blender/test_library_view.py": "a9e34b45135904e6c1b4d1cc5ed774e2ee47383cd8f9b8f2b0e1e5bfac505f3d",
      "tests/blender/test_asset_library.py": "0ca458607e9dc8bd11a7209ff300bd62dd209191a85278e5975a3bdc44cd33b8",
      "tests/blender/test_studio_view.py": "6e9b1ccbd76ea6a9c4909bf5f72fe374988012e0573037d0ef0ed9a2a9522880",
      "tests/blender/run_all.py": "bcce33605252d54bbc0e78e45f0806809c9ec1b515b0c0fe0e97f0a4372b0944"
    }
  }
}
---

Evidence for [the canonical guide](../../USER_GUIDE.md).
