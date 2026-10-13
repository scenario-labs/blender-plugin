---
{
  "type": "Evidence",
  "id": "docs-user-guide.native-workflow-controls",
  "title": "Native shared workflow input and approval controls",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "native-workflow-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "Source review of the current guide's Run a workflow steps 1 to 4 and its sentence that the form saves with the scene while prices and approvals do not survive a restart. The guide now keeps these steps short and links reference docs for upload detail. Checked against workflow_controls: the Private and Public buttons read that catalog; up to 40 rows, filtered by Search, each open the Load workflow inputs confirmation, as does the button beside the Workflow ID field; each input's include checkbox starts ticked when the input has a default or is always required, and an unticked input is left out of the payload; values are validated with forms and params before Request workflow price; Generate stays disabled as Generate (request price) until a current quote for the unchanged form exists, then opens a confirmation whose OK submits once. Also checked: the Workflows page in studio, the scene-saved form and its registration in registry, in-memory quotes, single use, the exact price, unchanged inputs and scene, and the online check in model_jobs and job_session, and the in-memory owner that runtime retires with the connection. The upload and Library parts of the file-input sentence belong to the workflow-input-uploads and workflow-library-references topics; this review only confirmed that a file input takes an asset ID and draws those controls, and that no upload is offered for a file input with listed allowed values or a kind other than image, audio, video or 3D. Installed tests in tests/blender/test_workflow_controls.py, with the shared fixture and quote lifecycle tests in tests/blender/test_workflow_commands.py, were read, not run: loading, pricing, single-use exact approval, changed inputs, pending metadata, page navigation, retired connections, reopening a saved form with its choices rebuilt, and always-required inputs. Offline unit tests in test_forms.py passed with the workflow cost topic's suites (337 tests). scenario/mcp/tools_scenario.py was removed as a source: the current guide makes no claim about MCP workflow commands, whose evidence belongs to docs/MCP.md. Not verified: native desktop interaction, screenshots, other operating systems, DPI and Blender versions, and live workflows. No paid or live service call was made. 2026-10-13 gallery note: refreshed after the guide gained an explorations gallery; the gallery doesn't touch the sections this topic covers, and its claims were not re-reviewed.",
    "sources": {
      "docs/USER_GUIDE.md": "a9e84d847e233ba08cacc75cc0fcbc8c0c7eae455e2862ff8584fe447d0bf90b",
      "scenario/blender/workflow_controls.py": "8b515b7c19fb0c6b4bc797a612a6158dac0bbecffb2a8254d259cb1a4ae956fd",
      "scenario/blender/runtime.py": "c8303eead552a5de421c69c56cb754c2d463f117909b46273c791d46275eb707",
      "scenario/blender/registry.py": "c3a880832b4cf47ce530ecea582a5c73e53c8f346d5a6521b7c023bab31cd9e3",
      "scenario/blender/studio.py": "41e0e0305bb47e3c82809fdfcddf34a89406198f2745e0009cfde697575b217c",
      "scenario/blender/model_jobs.py": "956e032cbe134fc57a3f0aa2e996a1f06388b80f8f0561b16bd703763995240e",
      "scenario/blender/job_session.py": "b20ae0be8fbec16510d6750fa50757f7830ebf937f65649e186c16ee9068fb28",
      "scenario/core/schema/forms.py": "6c13428b31421d71aa28f2f8fd2c95c7594eaa31fcadd49fc92782c462e274f6",
      "tests/blender/test_workflow_controls.py": "9128647ac6f788430919835a8d2d057bd7c426075b586a3c51c929fde8149578",
      "tests/blender/test_workflow_commands.py": "636c2e5a69c4a7a2e4a4aceff171d939af8bddb46a57d77d297fe661bbd1e312",
      "tests/blender/run_all.py": "bcce33605252d54bbc0e78e45f0806809c9ec1b515b0c0fe0e97f0a4372b0944",
      "scenario/core/schema/params.py": "1ba1ce2def667a7aef448aae35afe2c12372d747efa29fbfed9f9511978a7783"
    }
  }
}
---

Evidence for [the canonical guide](../../USER_GUIDE.md).
