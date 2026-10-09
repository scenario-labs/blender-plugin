---
{
  "type": "Evidence",
  "id": "tests-fixtures-readme.trained-model-contracts",
  "title": "tests/fixtures/README.md: trained-model contracts",
  "evidence": {
    "path": "tests/fixtures/README.md",
    "scope": "trained-model-contracts",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the recorder, its synthetic-service tests and every committed file under tests/fixtures/models/trained against the inventory rows and section: the fixed base and public trained IDs that must be in the public catalog, complete base records scrubbed with the shared account-field and signed-URL rules plus random non-public model and asset identifiers, routing-field projections that drop training parameters, placeholders for non-public parent and concept IDs, contracts.json fields, private records reduced to type, schema presence and statuses without reason text, exact replacement of the project, scope asset IDs, private record IDs and their non-public parents (a public parent of a private copy stays readable, so the leak check does not refuse the capture), the final leak check, whole-directory staging with restore on failure and a symlink refusal. Ten mutations of these safeguards each fail a test. The committed files were inspected for identifiers: remaining random model IDs are the six fixed public trained records and public flux.1-lora concept and parent records, asset IDs are placeholders and no signed URL remains. This is a targeted sanitizer, not proof that arbitrary service text is free of sensitive data; media rights and provenance of captured records remain under #9.",
    "sources": {
      "tests/fixtures/README.md": "ca3b4fb5928796a6e23f3c1244f16627462b3372eea27fe398512668576c5cc4",
      "tools/capture_trained_contracts.py": "10a3fd6256c1c579df24aa9b768b153c2462db38b5f2d9bd39c3ebf2a4ea3cf9",
      "tools/record_fixtures.py": "8a8afcee21fe4ab44be34186d22ed7a825167e6461231d29846bfca4d71840f2",
      "tests/unit/test_capture_trained_contracts.py": "9eaee4ca0a770fdd0bc164253c0fac54ddea079081cd72e4c397df2125fb8e31",
      "tests/unit/test_trained_contracts.py": "27ccb9cae8d115068c8c49647dd5da919843ed61f7cd96e51d04302b523bc038",
      "tests/unit/test_fixture_hygiene.py": "8e97a06f5805289a73ec456f8ccc536dd233372d5736c817eebb6c6253f97492",
      ".gitignore": "4ed96dcd0ee0b3f50d0250929543ff5622e3bcc79bb48a9ea1533dd89fd0e342",
      "tests/fixtures/models/trained/bases/model_bfl-flux-1-dev.json": "4a389b0ee2c856d04dcd1f5836934047f2acb0f73d9ff6f73af10d3fc7e47f3b",
      "tests/fixtures/models/trained/bases/model_bfl-flux-2-dev.json": "c2c91e6b77de181de21f78e4937b09a866ad0bf49aeddb304a12078fc9a27766",
      "tests/fixtures/models/trained/bases/model_flux-kontext-editing.json": "911c9e6b46233c355c13bd772e6bb4f49f6cdf7021e38a3f5edc75a2c889315d",
      "tests/fixtures/models/trained/bases/model_qwen-image-edit-2511.json": "8c08855a83fffca22319c8ab1dc36b4d186df368c69f38604f415f9a7ed62e15",
      "tests/fixtures/models/trained/bases/model_z-image.json": "d56a52275255b070dddd8e7a7e0e86fa3eb1057d74c2ff40718fa1f13a6ece9c",
      "tests/fixtures/models/trained/contracts.json": "15c19f7c77dd5dbc9c94b61a1cad8b3785a0105d7c4f21c984bdabf26e0fa779",
      "tests/fixtures/models/trained/public/model_2taP2G9BJL1Rw8t81NwiXGZA.json": "df22bf4013599feed5a7745f7a016900e56e7103f401d2678f444014963b34de",
      "tests/fixtures/models/trained/public/model_7oiHtKChpcLpy4jq3Jq2BG8n.json": "2a99a2463ebb3bd4566acd673b5496d70f6f2c3258a2066948a74811de4d1aab",
      "tests/fixtures/models/trained/public/model_CMUu7BjxV8TpdhG3FKoxZRxC.json": "54654904d9fc644ad64b68c72dd9e1a9fc9e6f1e132a8bf41e3c1f2b967da217",
      "tests/fixtures/models/trained/public/model_MYqiLuoTmgR2F1hzXPX3BBgY.json": "f34f40d84b1749a292609e2f0965b6da2bd3e3ddb7b5166509c0d7ec5d66f67d",
      "tests/fixtures/models/trained/public/model_YQrES2iPys22nYwh3YhVfMh8.json": "3b99cb78d677e9a6150176d41bd52b0a08d247ea35df313e3b3a776a503b2b2b",
      "tests/fixtures/models/trained/public/model_hFh8M6nQbqGFSKJdP536GXhE.json": "64e38863907b25a562992d17c6ea783a67a0253fa76f452dc8e9ec4b7f06b10a"
    }
  }
}
---

Evidence for [trained-model contracts](../../../tests/fixtures/README.md#trained-model-contracts).
