---
{
  "type": "Evidence",
  "id": "docs-model-payload-audit.hosted-acceptance",
  "title": "Hosted schema monitoring acceptance",
  "evidence": {
    "path": "docs/MODEL_PAYLOAD_AUDIT.md",
    "scope": "hosted-acceptance",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "88b6b3ec8ebd5707581f6d39f0fd158c784873a2",
    "limits": "Inspected scheduled success 37271766942 and its retained report, with zero fetch/schema failures and one MED advisory below HIGH. Confirmed two intentional missing-model failures 36136409761 and 36136541982 commented on the same closed issue 218. This closes issue 41 monitoring acceptance, not provider generation, future service behavior or release acceptance; no new live dispatch was performed.",
    "sources": {
      ".github/workflows/api-contract.yml": "05e92f742cf4430e7391b7f5b371792cd136c7dcfc9d69ade90785edaa3bef68",
      "tools/report_api_failure.py": "9857af0c95b92b7d984c679a617cbdea7136ebbc6784a08be199e33f17b2310a",
      "tools/report_ci_failure.py": "2e0cc31745a8897e7ca72a622642dbd9f76bf5a902cf0a8e7bc87195da30568e"
    }
  }
}
---

Evidence for [the canonical document](../../MODEL_PAYLOAD_AUDIT.md).
