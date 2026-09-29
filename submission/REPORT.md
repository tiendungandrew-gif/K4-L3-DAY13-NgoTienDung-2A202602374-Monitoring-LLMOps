# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Ngô Tiến Dũng
- **MSSV:** 2A202602374
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/tiendungandrew-gif/K4-L3-DAY13-NgoTienDung-2A202602374-Monitoring-LLMOps
- **Commit SHA cuối:**
- **Challenge ID:**
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602374`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Đã đạt chuẩn JSON schema, correlation ID propagation, enrichment và PII scrubbing |
| `validate_dashboard.py` | 6/6 panel | | Đã hợp lệ 6/6 panel contract |
| `pytest` | 22/22 passed | 24/24 passed | Pass toàn bộ test ban đầu và test PII mở rộng |
| Số traces hợp lệ | 0 / 10 | | Mới có root observation, chưa tách retrieval & generation |
| Số PII leak | 0 | 0 | Không còn rò rỉ PII trong structured logs |
| Latency P95 / TTFT P95 | 1333ms / 50ms | | Đo từ /metrics sau load test baseline |
| Retrieval success rate | 100% | | 30/30 request retrieval thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  - Trong `CorrelationIdMiddleware`, trước mỗi request thực hiện `clear_contextvars()` để tránh leak context giữa các request.
  - Lấy `correlation_id` từ request header `x-request-id`; nếu client không truyền thì tự sinh mã mới theo định dạng `req-<8-hex>` (`f"req-{uuid.uuid4().hex[:8]}"`).
  - Gắn ID vào structlog context qua `bind_contextvars(correlation_id=correlation_id)` và gán vào `request.state.correlation_id`.
  - Trả ID và thời gian xử lý về cho client qua header response: `x-request-id` và `x-response-time-ms`. Đồng thời truyền ID vào `agent.run()` để liên kết với Langfuse trace metadata.
- **Các metadata được ghi vào structured log:**
  - Metadata hệ thống bắt buộc: `ts` (ISO UTC), `level`, `service="api"`, `event`, `correlation_id`.
  - Metadata ngữ cảnh request: `user_id_hash` (băm SHA-256 rút gọn 12 ký tự của user_id), `session_id`, `feature`, `model`, `env` (được bind trước khi ghi log `request_received`).
  - Metadata hiệu năng & kết quả: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success` (trong `response_sent`) và `error_type` (khi `request_failed`).
- **Cách bảo đảm PII được scrub trước khi ghi:**
  - Cấu hình regex trong `PII_PATTERNS` cho email, số điện thoại Việt Nam, CCCD 12 số, và số thẻ tín dụng 16 số.
  - Cài đặt processor `scrub_event` đệ quy để quét và che toàn bộ chuỗi nhạy cảm thành `[REDACTED_<TYPE>]` trên tất cả các field của `event_dict`.
  - Đăng ký `scrub_event` vào pipeline của Structlog ngay trước `JsonlFileProcessor` và `JSONRenderer`. Nhờ đó dữ liệu được làm sạch hoàn toàn trước khi serialize JSON và ghi xuống file `data/logs.jsonl`.
- **Cách kiểm chứng kết quả:**
  - Chạy `python -m pytest -q`: 24/24 tests PASS (bao gồm các test che email, số điện thoại, CCCD, thẻ thanh toán).
  - Chạy `python scripts/validate_logs.py`: Đạt điểm tuyệt đối **100/100** (0 missing required fields, 0 missing context, 10/10 correlation IDs duy nhất, 0 PII leak).
  - Kiểm tra trực tiếp log thực tế trong `data/logs.jsonl` và response headers xác nhận correlation ID được truyền thông suốt.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
- **Cấu trúc root/retrieval/generation observations:**
- **Cách nối trace với log:**
- **Prompt name:**
- **Version/label baseline:**
- **Version/label candidate:**
- **Trace ID của mỗi version:**
- **Cách promote và rollback `production`:**

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
- **SLO và lý do chọn:**
- **Cách tính error budget:**
- **Ba alert và runbook tương ứng:**

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
