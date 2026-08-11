from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.dashboard import build_dashboard_snapshot


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_aggregates_all_six_contract_panels(tmp_path: Path) -> None:
    logs = tmp_path / "logs.jsonl"
    records = [
        {
            "ts": "2026-08-11T08:00:00Z",
            "event": "request_received",
        },
        {
            "ts": "2026-08-11T08:00:01Z",
            "event": "response_sent",
            "latency_ms": 1200,
            "tokens_in": 10,
            "tokens_out": 5,
            "cost_usd": 0.003,
            "quality_score": 0.8,
        },
        {
            "ts": "2026-08-11T08:01:00Z",
            "event": "request_received",
        },
        {
            "ts": "2026-08-11T08:01:01Z",
            "event": "request_failed",
            "error_type": "tool_timeout",
        },
    ]
    logs.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

    snapshot = build_dashboard_snapshot(
        logs,
        REPO_ROOT / "config" / "dashboard.yaml",
        end_at=datetime(2026, 8, 11, 8, 1, 1, tzinfo=timezone.utc),
    )

    assert set(snapshot["panels"]) == {
        "latency",
        "traffic",
        "errors",
        "cost",
        "tokens",
        "quality",
    }
    assert snapshot["panels"]["latency"]["values"]["p95"] == 1200.0
    assert snapshot["panels"]["traffic"]["values"]["count"] == 2
    assert snapshot["panels"]["errors"]["values"]["error_rate_pct"] == 50.0
    assert snapshot["panels"]["errors"]["values"]["count_by_value"] == {"tool_timeout": 1}
    assert snapshot["panels"]["cost"]["values"]["total"] == 0.003
    assert snapshot["panels"]["tokens"]["values"]["total"] == 15
    assert snapshot["panels"]["quality"]["values"]["mean"] == 0.8


def test_dashboard_uses_newest_log_as_default_window_end(tmp_path: Path) -> None:
    logs = tmp_path / "logs.jsonl"
    logs.write_text(
        json.dumps(
            {
                "ts": "2026-08-11T08:00:00Z",
                "event": "request_received",
            }
        ),
        encoding="utf-8",
    )

    snapshot = build_dashboard_snapshot(
        logs,
        REPO_ROOT / "config" / "dashboard.yaml",
    )

    assert snapshot["window"]["end"] == "2026-08-11T08:00:00Z"
    assert snapshot["window"]["start"] == "2026-08-11T07:00:00Z"
