from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from langfuse import Langfuse

EVIDENCE_DIR = REPO_ROOT / "submission" / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def export_all_evidence():
    client = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_BASE_URL"),
    )

    # 1. Export challenge trace with spans
    challenge_trace_id = "f2fa105729594bf8016090ea11c75b21"
    trace_obj = client.api.trace.get(challenge_trace_id)
    trace_dict = trace_obj.dict() if hasattr(trace_obj, "dict") else json.loads(json.dumps(trace_obj, default=str))
    
    (EVIDENCE_DIR / "challenge_incident_trace.json").write_text(
        json.dumps(trace_dict, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[+] Saved {EVIDENCE_DIR / 'challenge_incident_trace.json'}")

    # 2. Export all traces summary
    traces = client.api.trace.list(limit=50)
    traces_summary = [
        {
            "id": t.id,
            "name": t.name,
            "user_id": t.user_id,
            "session_id": t.session_id,
            "tags": t.tags,
            "metadata": t.metadata,
            "latency": getattr(t, "latency", None),
            "timestamp": str(t.timestamp),
        }
        for t in traces.data
    ]
    (EVIDENCE_DIR / "all_traces_list.json").write_text(
        json.dumps(traces_summary, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[+] Saved {EVIDENCE_DIR / 'all_traces_list.json'} ({len(traces_summary)} traces)")

    # 3. Generate waterfall breakdown document
    waterfall_md = f"""# Bằng chứng Điều tra Challenge: Cohort K4 (Incident: `rag_slow`)

## 1. Thông tin Challenge
- **Challenge ID**: `day13-k4-observability-v1`
- **Cohort**: `K4`
- **Incident**: `rag_slow`
- **Affected Feature**: `monitoring`
- **Latency Threshold**: `2000ms`
- **Trace ID tiêu biểu**: `{challenge_trace_id}`
- **Correlation ID**: `req-ea74853b`
- **Session ID**: `k4-challenge-s01`

---

## 2. Luồng chứng minh 3 trụ cột Observability

### Trụ cột 1: Metrics (Phát hiện sự cố)
- Snapshot từ endpoint `/metrics`:
  - `latency_p50`: `155.0 ms`
  - `latency_p95`: `2662.0 ms` (VƯỢT NGƯỠNG 2000ms và SLO p95)
  - `latency_p99`: `2662.0 ms`
  - `traffic`: `15` requests
  - `error_breakdown`: `{{}}`
- **Kết luận từ Metrics**: Độ trễ tail latency tăng đột biến từ mức bình thường (~700ms) lên trên 2600ms, tập trung vào các request gần nhất.

---

### Trụ cột 2: Traces (Khoanh vùng Span bất thường / Waterfall)
- Trace Link trên Langfuse Cloud: `https://cloud.langfuse.com/project/cmsocubpa01okad0imtxk9f7m/traces/{challenge_trace_id}`
- Cấu trúc Trace Waterfall:
  - **Trace**: `run` (Total Latency: `3.619s` / ~2.66s server-side)
    - **Span 1**: `rag_retrieval` (Observation ID: `e78c011eb65c5fa1`) -> **Duration: 2.505s** (Chiếm ~94% tổng thời gian thực thi)
    - **Span 2**: `FakeLLM.generate` (Generation ID: `f01bdb2647958afb`) -> **Duration: 0.150s** (Chiếm ~6% tổng thời gian)
- **Kết luận từ Trace Waterfall**: Span `rag_retrieval` là thủ phạm gây chậm toàn bộ pipeline, trong khi LLM generation hoạt động hoàn toàn bình thường.

---

### Trụ cột 3: Logs (Giải thích nguyên nhân gốc rễ và xác nhận context)
- Log line trong `data/logs.jsonl` có cùng `correlation_id` (`req-ea74853b`):
```json
{{"correlation_id": "req-ea74853b", "env": "dev", "event": "request_received", "feature": "monitoring", "level": "info", "model": "claude-sonnet-4-5", "payload": {{"message_preview": "Explain why metrics traces and logs work together."}}, "service": "api", "session_id": "k4-challenge-s01", "ts": "2026-08-11T08:36:34.880620Z", "user_id_hash": "f00ba60b3772"}}
{{"correlation_id": "req-ea74853b", "cost_usd": 0.002013, "env": "dev", "event": "response_sent", "feature": "monitoring", "latency_ms": 2660, "level": "info", "model": "claude-sonnet-4-5", "payload": {{"answer_preview": "Starter answer. Teams should improve this output logic and add better quality c..."}}, "quality_score": 0.9, "service": "api", "session_id": "k4-challenge-s01", "tokens_in": 38, "tokens_out": 126, "ts": "2026-08-11T08:36:37.540700Z", "user_id_hash": "f00ba60b3772"}}
```

---

## 3. Tổng kết Điều tra Incident

1. **Root Cause**:
   - Thành phần RAG vector retrieval (`mock_rag.py:retrieve()`) gặp hiện tượng nghẽn độ trễ khi xử lý các truy vấn thuộc feature `monitoring` (mô phỏng trễ 2.5s do vector store timeout/I/O bottleneck).
2. **Fix Action**:
   - Cấu hình timeout và fallback cho vector store query (ví dụ: timeout sau 500ms, nếu chậm thì sử dụng cached embeddings hoặc fallback corpus).
   - Tối ưu chỉ mục vector (HNSW index) và bổ sung connection pooling cho database/vector search.
3. **Preventive Measure**:
   - Thiết lập alert rule: Khi `latency_p95` của span `rag_retrieval` vượt quá `1500ms` trong cửa sổ 5 phút, gửi cảnh báo P1 cho team Data/RAG.
   - Bổ sung circuit breaker cho RAG service để tránh cascade failure làm treo API server.
"""
    (EVIDENCE_DIR / "challenge_trace_waterfall.md").write_text(waterfall_md, encoding="utf-8")
    print(f"[+] Saved {EVIDENCE_DIR / 'challenge_trace_waterfall.md'}")

    # 4. Run validators and pytest, save output to validation_results.txt
    val_logs = subprocess.run([sys.executable, "scripts/validate_logs.py"], capture_output=True, text=True, cwd=REPO_ROOT)
    val_dash = subprocess.run([sys.executable, "scripts/validate_dashboard.py"], capture_output=True, text=True, cwd=REPO_ROOT)
    val_pytest = subprocess.run([sys.executable, "-m", "pytest", "-v"], capture_output=True, text=True, cwd=REPO_ROOT)

    results_txt = f"""=== VALIDATE LOGS OUTPUT ===
{val_logs.stdout}
{val_logs.stderr}

=== VALIDATE DASHBOARD OUTPUT ===
{val_dash.stdout}
{val_dash.stderr}

=== PYTEST OUTPUT ===
{val_pytest.stdout}
{val_pytest.stderr}
"""
    (EVIDENCE_DIR / "validation_results.txt").write_text(results_txt, encoding="utf-8")
    print(f"[+] Saved {EVIDENCE_DIR / 'validation_results.txt'}")


if __name__ == "__main__":
    export_all_evidence()
