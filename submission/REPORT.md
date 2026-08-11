# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: A1
- Repository URL: [Github](https://github.com/endermagician15/Day13-K4-Observability)
- Commit SHA cuối: d486c0736f9b9b706a0ce8e9fb7b6e9b25747591
- Thành viên và vai trò:

| STT | Thành viên | MSSV | Vai trò phụ trách |
|---|---|---|---|
| 1 | Nguyễn Minh Hiếu | 2A202601816 | Logging & PII |
| 2 | Nguyễn Văn Đức | 2A202601422 | Tracing & Prompt Version |
| 3 | Đào Hải Đăng | 2A202601814 | Dashboard, SLO & Alerts |
| 4 | Vũ Xuân Đức | 2A202601668 | Incident, Report & Demo |

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (4/4 tiêu chí PASSED)
- Tổng số traces:
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard: chạy `python scripts/render_dashboard.py --output dashboard.html`, hoặc mở artifact [dashboard.html](evidence/dashboard.html).

## 3. Logging và tracing

- Evidence correlation ID: ![Correlation ID](evidence/corr_id.png)
- Evidence PII redaction: ![PII Redaction](evidence/REDACTED.png)
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.`
- Evidence dashboard: [Dashboard](evidence/dashboard.png), được render từ `data/logs.jsonl` bằng `scripts/render_dashboard.py`.
- Dashboard runtime hiển thị đúng sáu panel Latency (P50/P95/P99), Traffic, Errors, Cost, Tokens và Quality; cửa sổ mặc định 60 phút, refresh 30 giây, có đơn vị và threshold theo `config/dashboard.yaml`.
- SLO đã chọn và lý do: P95 latency ≤ 3000 ms (99.5%), error rate ≤ 2% (99.0%), daily cost ≤ 2.50 USD (100%) và quality score ≥ 0.75 (95%). Các ngưỡng này khớp với threshold trên dashboard để nối metric với hành động vận hành.
- Alert rules và runbook: `config/alert_rules.yaml` gồm
  `HighLatencyP95`, `HighErrorRate` và `LowQualityScore`; hướng dẫn nằm trong [docs/alerts.md](../docs/alerts.md).

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Nguyễn Minh Hiếu (2A202601816) | **Logging & PII:** Triển khai Middleware tự động khởi tạo và lan truyền `correlation_id`, bổ sung log context enrichment (`user_id_hash`, `session_id`, `feature`, `model`, `env`), xây dựng structlog processor đệ quy lọc khử dữ liệu PII nhạy cảm (Email, SĐT, CCCD, Thẻ credit, Passport). Đạt 100/100 điểm `validate_logs.py`. | [Commit / PR](#) | Hiểu rõ kiến trúc Structlog Processors Pipeline, cơ chế lan truyền Correlation ID qua ContextVars giữa các HTTP Request, và giải thuật đệ quy khử PII bảo vệ an toàn dữ liệu người dùng. |
| Nguyễn Văn Đức (2A202601422) | Tracing & Prompt Version | | |
| Đào Hải Đăng (2A202601814) | Dashboard, SLO & Alerts: xây dựng data layer và HTML renderer sáu panel; hoàn thiện SLO, alert rules và runbook; thêm test aggregation. | [d486c07](https://github.com/endermagician15/Day13-K4-Observability/commit/d486c07)| Hiểu cách giữ dashboard contract làm nguồn chuẩn, tính percentile/error rate/cost/token/quality từ JSONL và dùng threshold để dẫn hướng điều tra. |
| Vũ Xuân Đức (2A202601668) | Incident, Report & Demo | | |
