# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1: HighLatencyP95 (docs/alerts.md#alert-1)

- **Tên**: HighLatencyP95
- **Severity**: critical (P1)
- **SLI/SLO liên quan**: `latency_p95_ms <= 3000ms` (Target: 99.5%)
- **Điều kiện và thời gian duy trì**: `latency_p95 > 3000ms` liên tục trong `5 phút`
- **Ảnh hưởng tới người dùng**: Người dùng gặp hiện tượng phản hồi chậm hoặc treo request khi gửi câu hỏi tới AI API.
- **Ba bước kiểm tra đầu tiên**:
  1. Mở dashboard quan sát panel `Latency percentiles` để xác định phân bố độ trễ theo thời gian.
  2. Truy cập Langfuse Traces, lọc các trace có duration > 3000ms để xem span waterfall (xác định nghẽn ở `rag_retrieval` hay `LLM.generate`).
  3. Lấy `correlation_id` từ trace chậm, tra cứu trong `data/logs.jsonl` để kiểm tra error message, feature và model liên quan.
- **Mitigation tạm thời**: Bật cache kết quả tìm kiếm vector hoặc kích hoạt circuit breaker cho vector store, fallback về template phản hồi chuẩn.
- **Owner**: oncall-backend

## Alert 2: HighErrorRate (docs/alerts.md#alert-2)

- **Tên**: HighErrorRate
- **Severity**: critical (P0)
- **SLI/SLO liên quan**: `error_rate_pct <= 2%` (Target: 99.0%)
- **Điều kiện và thời gian duy trì**: `error_rate_pct > 2%` liên tục trong `5 phút`
- **Ảnh hưởng tới người dùng**: Người dùng nhận mã lỗi HTTP 500 / 503 khi gửi request, không nhận được câu trả lời.
- **Ba bước kiểm tra đầu tiên**:
  1. Kiểm tra panel `Errors` trên dashboard để xem tỷ lệ lỗi và breakdown theo `error_type` (e.g. `RuntimeError`, `TimeoutError`).
  2. Mở trace có trạng thái Error trên Langfuse để xem exception stack trace chi tiết.
  3. Kiểm tra log sự kiện `request_failed` trong `data/logs.jsonl` để định danh dependency bị sập.
- **Mitigation tạm thời**: Khởi động lại service hoặc chuyển traffic sang upstream model/fallback replica.
- **Owner**: oncall-backend

## Alert 3: LowQualityScore (docs/alerts.md#alert-3)

- **Tên**: LowQualityScore
- **Severity**: warning (P2)
- **SLI/SLO liên quan**: `quality_score_avg >= 0.75` (Target: 95.0%)
- **Điều kiện và thời gian duy trì**: `quality_avg < 0.75` liên tục trong `10 phút`
- **Ảnh hưởng tới người dùng**: Câu trả lời của AI bị suy giảm chất lượng, ngắn, thiếu ngữ cảnh tài liệu hoặc vi phạm chính sách.
- **Ba bước kiểm tra đầu tiên**:
  1. Kiểm tra panel `Quality proxy` trên dashboard để xem xu hướng điểm chất lượng.
  2. Mở các trace có `quality_score < 0.75` trên Langfuse, đối chiếu `prompt_version` và `prompt_label` đang được phục vụ.
  3. Nếu chất lượng giảm do prompt candidate mới, tiến hành rollback prompt version về baseline ngay lập tức.
- **Mitigation tạm thời**: Rollback `LANGFUSE_PROMPT_LABEL` về version ổn định trước đó.
- **Owner**: oncall-ai
