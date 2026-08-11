"""Render the contract-backed dashboard as a self-contained HTML file."""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.dashboard import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_LOG_PATH,
    DashboardDataError,
    build_dashboard_snapshot,
)
from scripts.validate_dashboard import DashboardConfigError, load_dashboard_config


def _format_value(value: Any, unit: str) -> str:
    if isinstance(value, float):
        text = f"{value:.4f}".rstrip("0").rstrip(".")
    else:
        text = str(value)
    suffixes = {
        "ms": " ms",
        "usd": " USD",
        "percent": "%",
        "requests_per_minute": " req/min",
        "tokens": " tokens",
        "score_0_to_1": " / 1.0",
    }
    return escape(text + suffixes.get(unit, f" {unit}"))


def _threshold_text(panel: dict[str, Any]) -> str:
    threshold = panel["threshold"]
    operator = "≤" if threshold["operator"] == "lte" else "≥"
    return f"{escape(str(threshold['aggregation']))} {operator} {_format_value(threshold['value'], panel['unit'])}"


def _status_label(status: str) -> str:
    return {"ok": "OK", "breach": "BREACH", "no_data": "NO DATA"}.get(status, status.upper())


def _bar_chart(series: list[dict[str, Any]], key: str, unit: str) -> str:
    values = [float(item[key]) for item in series if isinstance(item.get(key), (int, float))]
    if not values:
        return '<div class="empty-chart">No data in selected window</div>'
    maximum = max(max(values), 1.0)
    bars = []
    for value in values:
        height = max(4, round(value / maximum * 100))
        bars.append(
            f'<span class="bar" style="height:{height}%" title="{escape(_format_value(value, unit))}"></span>'
        )
    return '<div class="bar-chart" aria-label="Metric trend">' + "".join(bars) + "</div>"


def _value_rows(panel_id: str, panel: dict[str, Any]) -> str:
    values = panel["values"]
    labels = {
        "latency": {"p50": "P50", "p95": "P95", "p99": "P99"},
        "traffic": {"count": "Requests", "rate_per_minute": "Rate"},
        "errors": {"error_rate_pct": "Error rate", "failed_count": "Failed", "request_count": "Requests"},
        "cost": {"total": "Window total", "average_per_response": "Avg / response"},
        "tokens": {"tokens_in": "Input", "tokens_out": "Output", "total": "Total"},
        "quality": {"mean": "Mean score"},
    }
    rows = []
    for key, label in labels.get(panel_id, {}).items():
        if key not in values:
            continue
        unit = panel["unit"]
        if panel_id == "traffic" and key == "count":
            unit = "requests"
        if panel_id == "errors" and key in {"failed_count", "request_count"}:
            unit = "requests"
        rows.append(
            f'<div class="metric"><span>{escape(label)}</span><strong>{_format_value(values[key], unit)}</strong></div>'
        )
    return "".join(rows)


def render_dashboard(snapshot: dict[str, Any]) -> str:
    """Return a readable, dependency-free HTML dashboard."""

    panels = snapshot["panels"]
    chart_keys = {
        "latency": ("p95", "ms"),
        "traffic": ("requests", "requests"),
        "errors": ("error_rate_pct", "percent"),
        "cost": ("cost_usd", "usd"),
        "tokens": ("tokens_out", "tokens"),
        "quality": ("quality_score", "score_0_to_1"),
    }
    cards = []
    for panel_id in ("latency", "traffic", "errors", "cost", "tokens", "quality"):
        panel = panels[panel_id]
        status = panel["status"]
        chart_key, chart_unit = chart_keys[panel_id]
        breakdown = ""
        if panel_id == "errors":
            breakdown_items = panel["values"]["count_by_value"]
            breakdown = "".join(
                f'<span class="tag">{escape(str(name))}: {count}</span>'
                for name, count in breakdown_items.items()
            ) or '<span class="muted">No failures</span>'
        cards.append(
            f"""
            <article class="card">
              <div class="card-heading">
                <h2>{escape(panel['title'])}</h2>
                <span class="status {escape(status)}">{escape(_status_label(status))}</span>
              </div>
              <div class="metrics">{_value_rows(panel_id, panel)}</div>
              {_bar_chart(panel['series'], chart_key, chart_unit)}
              <div class="threshold">Threshold: {_threshold_text(panel)}</div>
              <div class="breakdown">{breakdown}</div>
            </article>
            """
        )

    start = escape(snapshot["window"]["start"])
    end = escape(snapshot["window"]["end"])
    refresh = int(snapshot["refresh_seconds"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="{refresh}">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(snapshot['title'])}</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; background:#0b1220; color:#e5edf8; }}
    body {{ margin:0; padding:28px; background:linear-gradient(145deg,#0b1220,#111d33); }}
    main {{ max-width:1280px; margin:auto; }}
    header {{ display:flex; justify-content:space-between; gap:18px; align-items:flex-end; margin-bottom:24px; }}
    h1 {{ margin:0 0 7px; font-size:28px; }}
    h2 {{ margin:0; font-size:16px; font-weight:650; }}
    .subtitle,.muted {{ color:#93a4be; font-size:13px; }}
    .window {{ text-align:right; color:#c4d1e5; font-size:13px; line-height:1.6; }}
    .grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; }}
    .card {{ min-height:208px; border:1px solid #253653; border-radius:14px; padding:18px; background:#121e32e8; box-shadow:0 10px 28px #05091455; }}
    .card-heading {{ display:flex; align-items:center; justify-content:space-between; gap:8px; }}
    .status {{ border-radius:999px; font-size:10px; font-weight:750; letter-spacing:.06em; padding:4px 8px; }}
    .status.ok {{ background:#123c35; color:#6ee7b7; }} .status.breach {{ background:#4a2029; color:#fda4af; }} .status.no_data {{ background:#333b49; color:#cbd5e1; }}
    .metrics {{ display:flex; flex-wrap:wrap; gap:10px; margin:20px 0 15px; }}
    .metric {{ display:flex; flex-direction:column; gap:3px; min-width:83px; }}
    .metric span {{ color:#93a4be; font-size:11px; }} .metric strong {{ font-size:19px; }}
    .bar-chart {{ display:flex; align-items:flex-end; gap:2px; height:48px; border-bottom:1px solid #33435e; margin:4px 0 13px; overflow:hidden; }}
    .bar {{ display:block; flex:1; min-width:2px; background:linear-gradient(#70a7ff,#3974d8); border-radius:2px 2px 0 0; opacity:.86; }}
    .empty-chart {{ color:#71839d; font-size:12px; height:48px; padding-top:16px; box-sizing:border-box; }}
    .threshold {{ color:#a9bad2; font-size:11px; }} .breakdown {{ display:flex; flex-wrap:wrap; gap:5px; margin-top:10px; min-height:17px; }}
    .tag {{ color:#c9d7ea; background:#1d2c45; border-radius:5px; padding:3px 6px; font-size:10px; }}
    footer {{ color:#71839d; font-size:12px; margin-top:18px; }}
    @media (max-width:900px) {{ .grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
    @media (max-width:620px) {{ body {{ padding:16px; }} header {{ display:block; }} .window {{ text-align:left; margin-top:10px; }} .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <div><h1>{escape(snapshot['title'])}</h1><div class="subtitle">Six-panel AI API observability dashboard · {snapshot['records_in_window']} records</div></div>
    <div class="window"><div><strong>Time range:</strong> last {snapshot['time_range_minutes']} minutes</div><div>{start} → {end}</div><div>Auto-refresh: {refresh}s</div></div>
  </header>
  <section class="grid">{''.join(cards)}</section>
  <footer>Source: data/logs.jsonl · Thresholds and units are read from config/dashboard.yaml</footer>
</main>
</body>
</html>
"""


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Render the six-panel Day 13 dashboard")
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "dashboard.html")
    args = parser.parse_args()

    try:
        load_dashboard_config(args.config)
        snapshot = build_dashboard_snapshot(args.logs, args.config)
        html = render_dashboard(snapshot)
    except (DashboardConfigError, DashboardDataError, OSError) as exc:
        print(f"Dashboard render failed: {exc}")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(
        f"Dashboard rendered: {args.output} "
        f"({len(snapshot['panels'])}/6 panels, {snapshot['records_in_window']} records)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
