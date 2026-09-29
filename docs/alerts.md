# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighLatencyP95Breach
- Severity: warning
- Duration: 5m
- Kênh thông báo: Slack (#llmops-alerts)
- SLI/SLO liên quan: Primary SLO `fast_successful_requests` (latency P95 <= 3000ms trong cửa sổ 28 ngày)
- Điều kiện và thời gian duy trì: `latency_p95 > 3000ms` duy trì liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: Người dùng cảm nhận độ trễ phản hồi chat chậm rõ rệt hoặc bị timeout.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Latency và TTFT trên Dashboard xem độ trễ tăng ở bước TTFT (mô hình LLM) hay tổng latency (retrieval vector DB).
  2. Lọc trong `data/logs.jsonl` các event `response_sent` có `latency_ms > 3000`, lấy một vài `correlation_id`.
  3. Mở Langfuse tìm trace tương ứng với `correlation_id` đó, xem waterfall để định vị span chậm (`retrieval` hay `fake-llm-generate`).
- Mitigation tạm thời:
  - Nếu do RAG vector search bị chậm: tạm thời bật cache kết quả hoặc giảm top_k.
  - Nếu do traffic quá tải: scale up thêm worker hoặc kích hoạt rate limit tạm thời.
- Owner: ngotiendung (oncall-backend)

## Alert 2

- Tên: HighRequestErrorRate
- Severity: critical
- Duration: 3m
- Kênh thông báo: Slack (#llmops-alerts)
- SLI/SLO liên quan: Guardrail `error_rate_pct_max <= 2.0%`
- Điều kiện và thời gian duy trì: `error_rate_pct > 2.0%` duy trì liên tục trong 3 phút.
- Ảnh hưởng tới người dùng: Người dùng nhận mã lỗi HTTP 500 hoặc thông báo gián đoạn dịch vụ.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Errors trên Dashboard xem loại lỗi (`error_type`) nào đang chiếm đa số.
  2. Tra `data/logs.jsonl` với query `event == "request_failed"` để xem `detail` và stack trace lỗi.
  3. Kiểm tra trạng thái các dependency downstream (vector store, model API) qua `/health`.
- Mitigation tạm thời:
  - Bật cơ chế circuit breaker hoặc trả lời fallback an toàn cho người dùng.
  - Nếu lỗi do bản deploy/prompt mới: rollback phiên bản code hoặc prompt về phiên bản ổn định trước đó.
- Owner: ngotiendung (oncall-backend)

## Alert 3

- Tên: RetrievalSuccessRateDrop
- Severity: warning
- Duration: 5m
- Kênh thông báo: Slack (#llmops-alerts)
- SLI/SLO liên quan: Guardrail `retrieval_success_rate_pct_min >= 90.0%`
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90.0%` duy trì liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: Mô hình không nhận được tài liệu ngữ cảnh, câu trả lời bị generic hoặc suy giảm chất lượng.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Errors & Retrieval Success trên Dashboard để xác định thời điểm tỷ lệ thành công bị sụt giảm.
  2. Kiểm tra log có `tool_name == "retrieval"` và `tool_success == false`.
  3. Mở Langfuse trace kiểm tra span `retrieval` xem vector store có báo lỗi timeout (`RuntimeError: Vector store timeout`) hay connection error không.
- Mitigation tạm thời:
  - Khởi động lại service RAG / vector index kết nối.
  - Tạm thời cho phép agent trả lời kèm cảnh báo "Hệ thống tra cứu tài liệu đang bảo trì".
- Owner: ngotiendung (oncall-rag-team)
