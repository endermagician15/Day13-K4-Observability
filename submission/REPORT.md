# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: A1
- Repository URL: [Github](https://github.com/endermagician15/Day13-K4-Observability)
- Commit SHA cuối: 
- Thành viên và vai trò:

| STT | Thành viên | MSSV | Vai trò phụ trách |
|---|---|---|---|
| 1 | Nguyễn Minh Hiếu | 2A202601816 | Logging & PII |
| 2 | Nguyễn Văn Đức | 2A202601422 | Tracing & Prompt Version |
| 3 | Đào Hải Đăng | 2A202601814 | Dashboard, SLO & Alerts |
| 4 | Vũ Xuân Đức | 2A202601668 | Incident, Report & Demo |

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100
- Tổng số traces:
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard:

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

- Kết quả `validate_dashboard.py`:
- Evidence dashboard:
- SLO đã chọn và lý do:
- Alert rules và runbook:

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
| Đào Hải Đăng (2A202601814) | Dashboard, SLO & Alerts | | |
| Vũ Xuân Đức (2A202601668) | Incident, Report & Demo | | |
