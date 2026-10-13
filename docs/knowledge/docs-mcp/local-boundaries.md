---
{
  "type": "Evidence",
  "id": "docs-mcp.local-boundaries",
  "title": "Local MCP request boundaries and agent file uploads",
  "description": "Host check, idle timeout and loopback bind of the local server, the agent upload allowlist and the default-start decision.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "local-boundaries",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "Reviewed server.py: host_allowed accepts only 127.0.0.1, localhost or bracketed [::1] in any letter case, with an optional decimal port from 1 to 65535; the handler's _admitted gate runs before routing, authentication and the Origin check for GET, POST, DELETE and OPTIONS, refusing a missing or repeated Host with 400 and any other name with 403 forbidden host through the existing _reject teardown; StreamRequestHandler applies McpServer's idle_timeout (IDLE_TIMEOUT 60 s by default, a positive finite override for tests) to each socket read and write, which the executor's wait for the main thread does not perform; McpServer refuses any bind host other than 127.0.0.1; process_pending marks agent tool execution for executing_tool. Reviewed upload_policy.py (~ expansion, strict link resolution, regular files only, one refusal for missing and outside paths, resolved containment in roots, ChosenFiles bounded at 256), reference_uploads.note_chosen_file and agent_upload_path (roots: extension_path_user plus the state and cache folders; blend-relative paths made absolute; choices recorded only outside executing_tool), the first_frame_path and workflow upload_path update callbacks, the Add reference operator behind the forms' Upload button, upload_reference uploading the resolved path, render_commands refusing an unallowed first frame before await_description and preparation, mcp_service and registry (GUI start when Online Access is on, explicit headless command, both binding 127.0.0.1), the stdio bridge's urllib requests and the manifest network permission (64 characters, accepted by make build's Blender validation). Unit tests: test_mcp_boundaries.py over real loopback sockets (rebinding Host on GET /health, GET and POST /mcp, DELETE, OPTIONS and an unknown path refused without dispatch; missing or repeated Host 400; Host checked before Origin and token; loopback hosts with and without port, including [::1]:port, reach /health and tools; idle, stalled-header, stalled-body and keep-alive connections closed with a 0.2 s idle timeout; a 0.6 s tool still answered), test_mcp_server.py (host parsing, refused binds, idle-timeout validation and default, execution mark), test_upload_policy.py (extension file and chosen file allowed; other file, link escaping a root, linked folder, dot-dot path and retargeted chosen link refused; missing file and folder refused with one message; no file opened on refusal) and test_manifest.py. Installed native tests in test_mcp_server.py and test_mcp_security.py cover the Host check, a 0.2 s idle close, refused binds, upload_reference by resolved path for an extension file and for files chosen through the first-frame field, a workflow File field and the Add reference operator executed as after a file-browser confirmation, refusals before ensure_reference_uploads or start, the client-facing UploadRefused text, a field set by a tool through McpServer.process_pending not recorded, and render_form first-frame refusal before preparation; test_reference_uploads.py now creates its wrong-type files inside the patched extension folder so its kind check still runs. The full installed suite (2013 tests, 3 Windows-only skips) passed on the exact packaged ZIP in an isolated profile on macOS arm64 Blender 5.1.2 only; Blender 5.0 and 5.2, Linux and Windows rely on hosted CI. Not established: a physical desktop file-browser pick (background tests assign the fields or execute the operator directly), the Host header of every third-party MCP client beyond HTTP/1.1's requirement, a bound on a client that sends a byte within each idle period, or any restriction while Python execution is enabled. No paid or live service call.",
    "sources": {
      "scenario/mcp/server.py": "775c22ecdb8e7aad7fec1044f431564812c60bc49febb7e1f6eb3e14d57fb29a",
      "scenario/mcp/upload_policy.py": "b2eec937e08ca92d659808692294286993fea428708d9b25489b642d80e9102d",
      "scenario/mcp/tools_scenario.py": "7f82a77aa9f76e6907f07d5a716e154a44a2a56735326d9cf20dbfbc5d52b007",
      "scenario/mcp/stdio_shim.py": "0d04b4b776711511460758cc7c00a83f88eb61a90cf9e7c46f0ca2bb270e8bb6",
      "scenario/blender/reference_uploads.py": "688f20c80bffe9ee16c602867ee1c03132e3f174c6bdaf866b0e9472bdca53ba",
      "scenario/blender/render_commands.py": "c49dd046a555163775183ddc51b67a0bc8e72798db9b3ca026e86ae8a9b9680c",
      "scenario/blender/props.py": "e54659bed4261351a8b1f7b1eeb5751bf17e2251c153d37dbc05b2b93cc219cb",
      "scenario/blender/workflow_controls.py": "31a09e870e27947c72018bb357f6be7203fd1adff1fb04d4144c31323da2da99",
      "scenario/blender/operators.py": "8881ad17a319551e5cfb3af00937651df50b4584adfa7b4221d506baa2269475",
      "scenario/blender/runtime.py": "8dcf8f33c7c65503d7f21aaee009a7b626da4a95c89bc8ffa00096c582b7ad0e",
      "scenario/blender/mcp_service.py": "f56b2020dadeef23ae089a5a649bbbb99fa4cba407994ebd8f3d12c1680495b9",
      "scenario/blender/registry.py": "c3a880832b4cf47ce530ecea582a5c73e53c8f346d5a6521b7c023bab31cd9e3",
      "scenario/blender_manifest.toml": "d9272c0810c168b1558ce0891fecf062a3974dcbc9bbae1a89777b911a1bfcef",
      "tests/unit/test_mcp_boundaries.py": "c005b2dcad4850f4d26f9dc94319b1a639cf67104fc3e00c1926af8f64d0f66f",
      "tests/unit/test_mcp_server.py": "fdac22d35ad7c8ff11a54356e082d62ba0665682ccdc99e98d35a71a6d71a6ae",
      "tests/unit/test_upload_policy.py": "7ded06734b745eea6099cabaa8982703451390b8d97beedb0013c5e180cdba26",
      "tests/unit/test_manifest.py": "44fbc7b386c73f44058ead517c82336638dca2777ad1acf62c287f181e2e6dba",
      "tests/blender/test_mcp_server.py": "2822c5ee916e990ac156422aa30c45242e19aafae0207011a16c507552f0245e",
      "tests/blender/test_mcp_security.py": "5f4c1301743a6258a268fcea7f4180aadba927f3a86f831979bbd02935c04958",
      "tests/blender/test_reference_uploads.py": "09d89d2e30c9c8b910c0ce8059154cafee32383f423f32b02bd77a057e08cc86"
    }
  }
}
---

# Local MCP request boundaries and agent file uploads

Evidence for [the canonical document](../../MCP.md): its request boundaries, agent
file uploads and the two recorded decisions, with the matching Security model,
Typed local references and Troubleshooting sentences.
