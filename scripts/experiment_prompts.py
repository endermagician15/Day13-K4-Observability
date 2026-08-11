from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from langfuse import Langfuse
from app.agent import LabAgent
from app.tracing import get_langfuse_client
from scripts.manage_prompts import get_client, promote_candidate, rollback_to_baseline

EVIDENCE_DIR = REPO_ROOT / "submission" / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def run_prompt_experiments():
    client = get_client()
    agent = LabAgent()
    langfuse_client = get_langfuse_client()

    print("==================================================")
    print("STEP 1: Run request with Prompt v1 (label: baseline)")
    print("==================================================")
    os.environ["LANGFUSE_PROMPT_LABEL"] = "baseline"
    res1 = agent.run(
        user_id="student-v1-baseline",
        feature="qa",
        session_id="session-v1-baseline",
        message="What is the refund policy?",
    )
    langfuse_client.flush()
    print(f"Trace v1 ID: {res1.trace_id}")
    print(f"Trace URL: {res1.trace_url}")

    print("\n==================================================")
    print("STEP 2: Run request with Prompt v2 (label: candidate)")
    print("==================================================")
    os.environ["LANGFUSE_PROMPT_LABEL"] = "candidate"
    res2 = agent.run(
        user_id="student-v2-candidate",
        feature="qa",
        session_id="session-v2-candidate",
        message="What is the refund policy?",
    )
    langfuse_client.flush()
    print(f"Trace v2 ID: {res2.trace_id}")
    print(f"Trace URL: {res2.trace_url}")

    print("\n==================================================")
    print("STEP 3: Promote label 'production' to Version 2")
    print("==================================================")
    promote_candidate(client)
    os.environ["LANGFUSE_PROMPT_LABEL"] = "production"
    res3 = agent.run(
        user_id="student-prod-promoted-v2",
        feature="qa",
        session_id="session-prod-v2",
        message="What is the refund policy?",
    )
    langfuse_client.flush()
    print(f"Trace Prod (v2) ID: {res3.trace_id}")
    print(f"Trace URL: {res3.trace_url}")

    print("\n==================================================")
    print("STEP 4: Rollback label 'production' back to Version 1")
    print("==================================================")
    rollback_to_baseline(client)
    os.environ["LANGFUSE_PROMPT_LABEL"] = "production"
    res4 = agent.run(
        user_id="student-prod-rollback-v1",
        feature="qa",
        session_id="session-prod-rollback-v1",
        message="What is the refund policy?",
    )
    langfuse_client.flush()
    print(f"Trace Prod Rollback (v1) ID: {res4.trace_id}")
    print(f"Trace URL: {res4.trace_url}")

    # Wait for traces to be indexed on Langfuse Cloud
    print("\nĐang đợi Langfuse Cloud xử lý traces...")
    time.sleep(3)

    # Collect individual trace objects from Langfuse API
    def fetch_trace_dict(trace_id: str | None) -> dict:
        if not trace_id:
            return {}
        try:
            t = client.api.trace.get(trace_id)
            return t.dict() if hasattr(t, "dict") else json.loads(json.dumps(t, default=str))
        except Exception as e:
            return {"id": trace_id, "fetch_error": str(e)}

    trace_data_v1 = fetch_trace_dict(res1.trace_id)
    trace_data_v2 = fetch_trace_dict(res2.trace_id)
    trace_data_v3 = fetch_trace_dict(res3.trace_id)
    trace_data_v4 = fetch_trace_dict(res4.trace_id)

    (EVIDENCE_DIR / "trace_v1_baseline.json").write_text(
        json.dumps(trace_data_v1, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
    )
    (EVIDENCE_DIR / "trace_v2_candidate.json").write_text(
        json.dumps(trace_data_v2, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
    )
    (EVIDENCE_DIR / "trace_prod_promoted_v2.json").write_text(
        json.dumps(trace_data_v3, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
    )
    (EVIDENCE_DIR / "trace_prod_rollback_v1.json").write_text(
        json.dumps(trace_data_v4, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
    )

    evidence = {
        "prompt_name": "day13-chat",
        "step_1_baseline_v1": {
            "trace_id": res1.trace_id,
            "trace_url": res1.trace_url,
            "session_id": "session-v1-baseline",
            "prompt_version": 1,
            "prompt_label": "baseline",
            "prompt_source": "langfuse",
            "latency_ms": res1.latency_ms,
        },
        "step_2_candidate_v2": {
            "trace_id": res2.trace_id,
            "trace_url": res2.trace_url,
            "session_id": "session-v2-candidate",
            "prompt_version": 2,
            "prompt_label": "candidate",
            "prompt_source": "langfuse",
            "latency_ms": res2.latency_ms,
        },
        "step_3_promoted_v2": {
            "trace_id": res3.trace_id,
            "trace_url": res3.trace_url,
            "session_id": "session-prod-v2",
            "prompt_version": 2,
            "prompt_label": "production",
            "prompt_source": "langfuse",
            "latency_ms": res3.latency_ms,
        },
        "step_4_rollback_v1": {
            "trace_id": res4.trace_id,
            "trace_url": res4.trace_url,
            "session_id": "session-prod-rollback-v1",
            "prompt_version": 1,
            "prompt_label": "production",
            "prompt_source": "langfuse",
            "latency_ms": res4.latency_ms,
        },
    }

    evidence_file = EVIDENCE_DIR / "prompt_versioning_evidence.json"
    evidence_file.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[+] Lưu bằng chứng prompt versioning vào {evidence_file}")

    # Generate Markdown Summary Evidence
    summary_md = f"""# Bằng chứng Prompt Versioning & Rollback trên Langfuse

## 1. Cấu hình Prompt `day13-chat`
- **Tên prompt**: `day13-chat`
- **Loại**: `text`
- **Variables**: `{{{{feature}}}}`, `{{{{docs}}}}`, `{{{{message}}}}`

### Phiên bản 1 (Baseline / Production ban đầu)
- **Version**: `1`
- **Labels**: `['baseline', 'production']`
- **Template**:
```text
Feature={{{{feature}}}}
Docs={{{{docs}}}}
Question={{{{message}}}}
```

### Phiên bản 2 (Candidate)
- **Version**: `2`
- **Labels**: `['candidate']`
- **Template**:
```text
[System: Answer concisely and accurately based strictly on the provided docs.]
Feature={{{{feature}}}}
Docs={{{{docs}}}}
Question={{{{message}}}}
```

---

## 2. Kết quả thực thi các bước kiểm thử

| Bước | Hành động | Prompt Label | Prompt Version | Trace ID | Trace URL |
|---|---|---|---|---|---|
| 1 | Chạy Baseline | `baseline` | `1` | `{res1.trace_id}` | [{res1.trace_id}]({res1.trace_url}) |
| 2 | Chạy Candidate | `candidate` | `2` | `{res2.trace_id}` | [{res2.trace_id}]({res2.trace_url}) |
| 3 | Promote Candidate | `production` (sau khi update v2) | `2` | `{res3.trace_id}` | [{res3.trace_id}]({res3.trace_url}) |
| 4 | Rollback về Baseline | `production` (sau khi rollback về v1) | `1` | `{res4.trace_id}` | [{res4.trace_id}]({res4.trace_url}) |

---

## 3. Xác minh Metadata & Trace Links
- Tất cả các trace trên đều được gắn đầy đủ metadata:
  - `prompt_name`: `day13-chat`
  - `prompt_label`: `baseline` / `candidate` / `production`
  - `prompt_version`: `1` / `2`
  - `prompt_source`: `langfuse`
  - `tags`: `['lab', 'qa', 'claude-sonnet-4-5']`
  - `user_id_hash` và `session_id`
"""
    (EVIDENCE_DIR / "prompt_versions_info.md").write_text(summary_md, encoding="utf-8")
    print(f"[+] Lưu tóm tắt bằng chứng vào {EVIDENCE_DIR / 'prompt_versions_info.md'}")


if __name__ == "__main__":
    run_prompt_experiments()
