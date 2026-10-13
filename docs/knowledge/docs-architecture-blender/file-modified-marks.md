---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.file-modified-marks",
  "title": "Marking the file modified",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "scope": "file-modified-marks",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "df2fac37c5e605854718811ffaf74384d8341033",
    "limits": "Inspected every local MCP tool and main-thread application path for Blender data changes outside an Undo operator, and the shared file_state helper they now call: one ed.undo_push per completed change, marks only after an actual change (validation before the first write, or file_state.marking comparing the data a command may change), the first window when the context has none, deferral during sculpt, paint and paint-curve strokes until the next pump tick, a dropped mark on file read, and no second step after saved model, mesh or first-frame checkpoints. Blender 5.1.2 source (ED_undo_push, ED_OT_undo_push, timer context) reviewed; pushes tag no ID and run no dependency or history handler, checked against a captured session origin. Installed evidence: the 52 tests in tests/blender/test_file_modified.py pass on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Against the main branch's call paths with only the unwired helper present, 27 of the first 38 fail; against the previous head, 8 of the review tests for refusals, unchanged state and part-way failures fail. The full installed suite passes on 5.1.2 (1981 tests, 3 Windows-only skips). Blender 5.0 reports every background file as modified, so its runs check the recorded marks and pushes. No desktop quit prompt, live stroke deferral, GUI timer context or Linux/Windows run is recorded here; CI runs the helper and scene-tool classes in the baseline.",
    "sources": {
      "scenario/blender/file_state.py": "899f1eb5423a4d366a7a491a22c8ca08beec4cb83a2b48422abf29ff4de48739",
      "scenario/blender/job_session.py": "1e4715d6a590a15684cfdf8fa956963b26889d6b147c9c745264e06557448138",
      "scenario/blender/model_jobs.py": "bc88dc2c30a6a960cc9b81748584ad80130bc4f7d1647486e0878ae4d349b8bc",
      "scenario/blender/first_frame_handoff.py": "3d931d0a3dcaec027577a94408ccea0a090f7e41c6a89ff589ffeb514f365caf",
      "scenario/blender/prompt_jobs.py": "c2ff180e68b6586f87d41475963d057b24a41b7c54cc6a439ed1d3ca9714d6b4",
      "scenario/blender/blockout_jobs.py": "45f847d5d0269d453bd284c8494be70aefb405264089d9f09ee42187ecabb5c2",
      "scenario/blender/workflow_controls.py": "6f523d6a18cc8d0f6cdaa12b037ffdf7797999e0a336cdc5f96128b5eb24057a",
      "scenario/blender/reference_form.py": "e3828f6fa358e31c45c316e6452e542ca717a7eef646865f4aba6c3f2b4e0df5",
      "scenario/blender/workflow_uploads.py": "39fc4d14f4617c0e27ab0ee27676e5adf537b4dfff2d379ba2666e1afe2cc692",
      "scenario/blender/film.py": "e03d6cd281184ac147f80c8f6beaaae429d7e4c3d0f7f02c1afcfb860e16cb0d",
      "scenario/blender/render_commands.py": "4ff7215af2bab9cbe1cfc6d2aa712e124f646feaeb406fc35ed4799266c6ae4a",
      "scenario/blender/world_application.py": "60e5fd73a02cbbc7ef67d52665ae9a70b4425432a7e68ae8484b99975b2718db",
      "scenario/blender/pump.py": "0c53227fe2f22b1d24963eb0a9ceaac32a35f35afc5f8cb058ee6ed0ee178dec",
      "scenario/blender/registry.py": "c3a880832b4cf47ce530ecea582a5c73e53c8f346d5a6521b7c023bab31cd9e3",
      "scenario/mcp/tools_blender.py": "155729533a747d1ec88d36b4cbb7e7cbe12cc6984090ba31b7adbdd2714da388",
      "scenario/mcp/tools_scenario.py": "3f9f25fb25690ddbf0bb0867b37e262cc46ab34ca022f7902c27c98e5560e2d9",
      "tests/blender/test_file_modified.py": "de19155d1a3c15f5a95f7dbd52bad686a9de48989b8333fff8bd060ab028d4a7",
      "tests/blender/helpers.py": "d1fe2a0d2f92597a112a9e18d46c3d9ea5fa705b48b59d44ece356cd4bb884eb",
      "tests/blender/run_all.py": "bcce33605252d54bbc0e78e45f0806809c9ec1b515b0c0fe0e97f0a4372b0944",
      "scenario/blender/generation.py": "659375e5892d3387e464f4531be08ec5d3a03ec84cbffed162a495d6310317d4",
      "scenario/blender/params_ui.py": "bd98b02f3b54878340617c308387ba90ce953cff94804f9d2f16ddc6f22c230e"
    }
  }
}
---

# Marking the file modified

Evidence for [the canonical guide](../../architecture/blender.md).
