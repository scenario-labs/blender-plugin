---
{
  "type": "Evidence",
  "id": "docs-mcp.local-mcp",
  "title": "docs/MCP.md: local mcp",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/MCP.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Tool table generated without importing Blender and compared with the installed native registry. Local setup/security claims inspected against active code. Exact-ZIP isolated Blender 5.0.1 macOS arm64 checks passed, including GUI authenticated tools/list with synthetic local credentials, Python disabled and external sockets blocked. Hosted tool mapping and Codex configuration checked against their official references. No paid generation, live provider, complete client/platform compatibility or shared-runtime acceptance is claimed. Sandbox provenance docstring and required formatting reviewed; executable AST is unchanged, with no new runtime acceptance claimed. Early HTTP rejection teardown, strict body framing and bounded drain inspected with loopback TCP deadline/no-dispatch regressions and installed native coverage; the original Windows reset is observed CI evidence, not a locally reproduced Windows result.",
    "sources": {
      "scenario/blender/mcp_service.py": "ec45907c26301d5c0c2e48fe2eab09136cd52aadb00c6be5401d23ec7d868715",
      "scenario/mcp/cli.py": "733ec02de0f03a9bfb0a9326a8f94ac32a2b6c33a5c11a09b79694cabd87c156",
      "scenario/mcp/protocol.py": "62b2fbfa2f3e4bcb6f8084f3b67798d97fe11c01a4ba38b062ddf52c8c68413b",
      "scenario/mcp/sandbox.py": "2f3423a7cfdc897c7860f220616c232a1f853332bf235b4f7f110eb5a39bd684",
      "scenario/mcp/server.py": "37ddc80b29d9f0df62617f169c982317f706dfda2883181bf0209f95722d3d50",
      "scenario/mcp/stdio_shim.py": "93d3091ffc43ef479953b0a72c359ac1ff3efa6a2d59d7d93f73e8ac8ebc0690",
      "scenario/mcp/tools_blender.py": "e80a60e846adae80dbf520cf969c1d14a11a03f4292b20b3394806ee5e4d0e4f",
      "scenario/mcp/tools_scenario.py": "66e90694c9bc89878cec3ed2c133ac017492c9ebec866e1c850c07baf4b29543",
      "tests/blender/test_mcp_contracts.py": "14db7e13774c4b3c94182c42ae33676ff37b87e4e869fe5e382a82349e2b04f0",
      "tests/blender/test_mcp_server.py": "c0bb48eaa71b73dfe3154b7505e54540a778939f1e98745013004675cefccd78",
      "tests/unit/test_mcp_descriptions.py": "79a43ea44a737d836f1192fefc2c25b2bb3a9db5edac7b238dab39bbbbf9ef31",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd",
      "tests/unit/test_mcp_rejection.py": "fc7ac3502222bb8b7e63a2a77e855fac96991f36541b4b2ad027b9430f7b61b7",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e"
    },
    "scope": "local-mcp",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/MCP.md: local mcp

Evidence for [the canonical document](../../MCP.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
