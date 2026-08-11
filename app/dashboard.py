"""Dashboard data preparation for the six-panel observability dashboard.

The dashboard contract deliberately stays in ``config/dashboard.yaml``.  This
module only translates the JSONL event stream into values that a renderer can
display, so the same calculations can be used by a CLI, a notebook, or a web
UI without duplicating metric logic.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

import yaml

from app.metrics import percentile


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
REQUIRED_PANEL_IDS = (
    "latency",
    "traffic",
    "errors",
    "cost",
    "tokens",
    "quality",
)


class DashboardDataError(ValueError):
    """Raised when the dashboard input cannot be interpreted safely."""


def _parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and normalize it to UTC."""

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise DashboardDataError(f"Invalid log timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _round(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


def load_log_records(path: Path = DEFAULT_LOG_PATH) -> list[dict[str, Any]]:
    """Load JSONL records and attach a normalized timestamp to each record.

    Empty lines are ignored.  A malformed record is reported with its line
    number instead of being silently dropped, because silently losing events
    would make an operational dashboard misleading.
    """

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise DashboardDataError(f"Log source not found: {path}") from exc

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DashboardDataError(
                f"Invalid JSON at {path}:{line_number}: {exc.msg}"
            ) from exc
        if not isinstance(record, dict):
            raise DashboardDataError(f"Log record at {path}:{line_number} is not an object")
        timestamp = record.get("ts")
        if not isinstance(timestamp, str):
            raise DashboardDataError(f"Log record at {path}:{line_number} has no string 'ts'")
        event = record.get("event")
        if not isinstance(event, str) or not event:
            raise DashboardDataError(
                f"Log record at {path}:{line_number} has no non-empty 'event'"
            )
        normalized = dict(record)
        normalized["_timestamp"] = _parse_timestamp(timestamp)
        records.append(normalized)
    return records


def _load_contract(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DashboardDataError(f"Dashboard config not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise DashboardDataError(f"Dashboard config is not valid YAML: {exc}") from exc

    dashboard = payload.get("dashboard") if isinstance(payload, dict) else None
    if not isinstance(dashboard, dict):
        raise DashboardDataError("Dashboard config is missing the 'dashboard' object")
    panels = dashboard.get("panels")
    if not isinstance(panels, list):
        raise DashboardDataError("Dashboard config is missing its panel list")
    by_id = {panel.get("id"): panel for panel in panels if isinstance(panel, dict)}
    missing = [panel_id for panel_id in REQUIRED_PANEL_IDS if panel_id not in by_id]
    if missing:
        raise DashboardDataError(f"Dashboard config is missing panels: {', '.join(missing)}")
    return dashboard


def _minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def _bucket_times(start: datetime, end: datetime) -> list[datetime]:
    current = _minute(start)
    last = _minute(end)
    buckets: list[datetime] = []
    while current <= last:
        buckets.append(current)
        current += timedelta(minutes=1)
    return buckets


def _records_by_minute(records: Iterable[dict[str, Any]]) -> dict[datetime, list[dict[str, Any]]]:
    grouped: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[_minute(record["_timestamp"])].append(record)
    return grouped


def _response_values(records: Iterable[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for record in records:
        value = _as_number(record.get(field))
        if value is not None:
            values.append(value)
    return values


def _percentiles(values: list[float]) -> dict[str, float]:
    # app.metrics is also used by the API /metrics endpoint.  Reusing it keeps
    # the dashboard and the service endpoint consistent for the same sample.
    integer_values = [int(round(value)) for value in values]
    return {
        "p50": _round(percentile(integer_values, 50)),
        "p95": _round(percentile(integer_values, 95)),
        "p99": _round(percentile(integer_values, 99)),
    }


def _threshold_status(value: float, threshold: dict[str, Any], has_data: bool) -> str:
    if not has_data:
        return "no_data"
    target = threshold["value"]
    operator = threshold["operator"]
    passed = value <= target if operator == "lte" else value >= target
    return "ok" if passed else "breach"


def _panel(
    panel_config: dict[str, Any],
    values: dict[str, Any],
    series: list[dict[str, Any]],
    check_value: float,
    has_data: bool,
) -> dict[str, Any]:
    threshold = dict(panel_config["threshold"])
    return {
        "id": panel_config["id"],
        "title": panel_config["title"],
        "unit": panel_config["unit"],
        "values": values,
        "series": series,
        "threshold": threshold,
        "threshold_value": _round(check_value),
        "status": _threshold_status(check_value, threshold, has_data),
    }


def build_dashboard_snapshot(
    log_path: Path = DEFAULT_LOG_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    *,
    end_at: datetime | None = None,
) -> dict[str, Any]:
    """Aggregate a log window according to the dashboard contract.

    If ``end_at`` is omitted, the newest log timestamp is used.  This makes a
    sparse fixture useful while retaining deterministic behavior; live callers
    can pass the current UTC time explicitly.
    """

    dashboard = _load_contract(config_path)
    records = load_log_records(log_path)
    if end_at is None:
        end = max(
            (record["_timestamp"] for record in records),
            default=datetime.now(timezone.utc),
        )
    else:
        end = end_at
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        end = end.astimezone(timezone.utc)

    window_minutes = dashboard.get("time_range_minutes", 60)
    if not isinstance(window_minutes, int) or window_minutes <= 0:
        raise DashboardDataError("Dashboard time_range_minutes must be a positive integer")
    start = end - timedelta(minutes=window_minutes)
    window_records = [
        record
        for record in records
        if start <= record["_timestamp"] <= end
    ]
    grouped = _records_by_minute(window_records)
    buckets = _bucket_times(start, end)

    responses = [record for record in window_records if record["event"] == "response_sent"]
    requests = [record for record in window_records if record["event"] == "request_received"]
    failures = [record for record in window_records if record["event"] == "request_failed"]

    latency_values = _response_values(responses, "latency_ms")
    latency_values_by_minute = {
        bucket: _response_values(
            [record for record in grouped.get(bucket, []) if record["event"] == "response_sent"],
            "latency_ms",
        )
        for bucket in buckets
    }
    latency_series = [
        {"timestamp": _iso(bucket), **_percentiles(values)}
        for bucket, values in latency_values_by_minute.items()
        if values
    ]

    traffic_series = [
        {
            "timestamp": _iso(bucket),
            "requests": sum(record["event"] == "request_received" for record in grouped.get(bucket, [])),
        }
        for bucket in buckets
    ]
    error_series: list[dict[str, Any]] = []
    cost_series: list[dict[str, Any]] = []
    token_series: list[dict[str, Any]] = []
    quality_series: list[dict[str, Any]] = []
    for bucket in buckets:
        bucket_records = grouped.get(bucket, [])
        bucket_requests = sum(record["event"] == "request_received" for record in bucket_records)
        bucket_failures = sum(record["event"] == "request_failed" for record in bucket_records)
        bucket_responses = [record for record in bucket_records if record["event"] == "response_sent"]
        bucket_cost = sum(_response_values(bucket_responses, "cost_usd"))
        bucket_quality = _response_values(bucket_responses, "quality_score")
        error_series.append(
            {
                "timestamp": _iso(bucket),
                "error_rate_pct": _round(bucket_failures / bucket_requests * 100)
                if bucket_requests
                else 0.0,
            }
        )
        cost_series.append({"timestamp": _iso(bucket), "cost_usd": _round(bucket_cost, 6)})
        token_series.append(
            {
                "timestamp": _iso(bucket),
                "tokens_in": int(sum(_response_values(bucket_responses, "tokens_in"))),
                "tokens_out": int(sum(_response_values(bucket_responses, "tokens_out"))),
            }
        )
        if bucket_quality:
            quality_series.append(
                {"timestamp": _iso(bucket), "quality_score": _round(mean(bucket_quality))}
            )

    error_breakdown = Counter(
        str(record.get("error_type", "unknown"))
        for record in failures
    )
    total_cost = sum(_response_values(responses, "cost_usd"))
    tokens_in = int(sum(_response_values(responses, "tokens_in")))
    tokens_out = int(sum(_response_values(responses, "tokens_out")))
    quality_values = _response_values(responses, "quality_score")
    error_rate = len(failures) / len(requests) * 100 if requests else 0.0
    elapsed_minutes = max(window_minutes, 1)
    request_rate = len(requests) / elapsed_minutes

    panel_config = {
        panel["id"]: panel for panel in dashboard["panels"] if isinstance(panel, dict)
    }
    panels = {
        "latency": _panel(
            panel_config["latency"],
            _percentiles(latency_values),
            latency_series,
            _percentiles(latency_values)["p95"],
            bool(latency_values),
        ),
        "traffic": _panel(
            panel_config["traffic"],
            {
                "count": len(requests),
                "rate_per_minute": _round(request_rate),
            },
            traffic_series,
            request_rate,
            bool(requests),
        ),
        "errors": _panel(
            panel_config["errors"],
            {
                "error_rate_pct": _round(error_rate),
                "count_by_value": dict(sorted(error_breakdown.items())),
                "failed_count": len(failures),
                "request_count": len(requests),
            },
            error_series,
            error_rate,
            bool(requests),
        ),
        "cost": _panel(
            panel_config["cost"],
            {
                "total": _round(total_cost, 6),
                "average_per_response": _round(total_cost / len(responses), 6)
                if responses
                else 0.0,
            },
            cost_series,
            total_cost,
            bool(responses),
        ),
        "tokens": _panel(
            panel_config["tokens"],
            {"tokens_in": tokens_in, "tokens_out": tokens_out, "total": tokens_in + tokens_out},
            token_series,
            tokens_in + tokens_out,
            bool(responses),
        ),
        "quality": _panel(
            panel_config["quality"],
            {"mean": _round(mean(quality_values)) if quality_values else 0.0},
            quality_series,
            mean(quality_values) if quality_values else 0.0,
            bool(quality_values),
        ),
    }
    return {
        "title": dashboard.get("title", "AI Observability Dashboard"),
        "time_range_minutes": window_minutes,
        "refresh_seconds": dashboard.get("refresh_seconds", 30),
        "window": {"start": _iso(start), "end": _iso(end)},
        "records_in_window": len(window_records),
        "panels": panels,
    }
