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
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Hợp lệ 100% contract 6 panel trong config/dashboard.yaml |
| `pytest` | 22/22 passed | 24/24 passed | Pass toàn bộ test ban đầu và test PII mở rộng |
| Số traces hợp lệ | 0 / 10 | 47 traces | Đầy đủ quan hệ cha-con: root (agent), retrieval và generation |
| Số PII leak | 0 | 0 | Không còn rò rỉ PII trong structured logs |
| Latency P95 / TTFT P95 | 1333ms / 50ms | 159ms / 50ms | Đo từ load test sau khi tích hợp child observations |
| Retrieval success rate | 100% | 100% | Toàn bộ các request retrieval đều thành công |

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
  - Traces được gửi về đúng project Langfuse cá nhân `day13-k4-l3a-2A202602374` thông qua API key và Secret key riêng trong `.env`.
  - Mọi trace đều chứa metadata `correlation_id` trùng khớp với correlation ID trong file log `data/logs.jsonl`, kèm tags `["lab", feature, "claude-sonnet-4-5"]` và `environment: "dev"`.
- **Cấu trúc root/retrieval/generation observations:**
  - Root observation: `lab-agent-run` (type `AGENT`, `is_root_observation: true`).
  - Child observation 1: `retrieval` (type `RETRIEVER`, có `parent_observation_id` trỏ về root `lab-agent-run`), ghi nhận thời gian tra cứu tài liệu từ corpus.
  - Child observation 2: `fake-llm-generate` (type `GENERATION`, có `parent_observation_id` trỏ về root `lab-agent-run`), ghi nhận `model="claude-sonnet-4-5"`, token usage (`input_tokens`, `output_tokens`, `total`), chi phí `cost_details`, `ttft_ms` và liên kết prompt template.
- **Cách nối trace với log:**
  - Khi request đi qua `CorrelationIdMiddleware`, ID được gán vào `request.state.correlation_id`.
  - Giá trị này vừa được bind vào Structlog context (ghi vào từng dòng log trong `data/logs.jsonl`), vừa được truyền vào `propagate_attributes(metadata={"correlation_id": correlation_id})` của Langfuse trace.
  - Khi điều tra sự cố, chỉ cần lấy `correlation_id` từ dòng log bất thường và tìm kiếm trực tiếp trên thanh filter của Langfuse sẽ ra ngay trace tương ứng.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (gắn label `baseline`, ban đầu mang label `production`)
- **Version/label candidate:** Version 2 (gắn label `candidate`, bổ sung hướng dẫn "Respond concisely in bullet points.")
- **Trace ID của mỗi version:**
  - Trace ID cho Version 1 (`baseline`/`production`): `ea49a4ebbb7a255fe21925537d8f94ce` (và trace sau rollback: `ffca7f8163693b761c04f264681ca429`)
  - Trace ID cho Version 2 (`candidate`/promoted): `5480ed54e5a38ed37526975bff94c315` (và trace sau promote: `721ee3ec18d832f69a6469a246e7b91d`)
- **Cách promote và rollback `production`:**
  - **Promote:** Chuyển label `production` sang Version 2 qua Langfuse UI hoặc SDK: `client.update_prompt(name="day13-chat", version=2, new_labels=["production", "candidate"])` và xóa cache `client.clear_prompt_cache()`.
  - **Rollback:** Khi cần quay lại bản ổn định trước đó, chuyển label `production` về lại Version 1: `client.update_prompt(name="day13-chat", version=1, new_labels=["production", "baseline"])` và xóa cache. Ứng dụng ngay lập tức nạp lại prompt v1 mà không cần sửa code hay restart server.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  - Thiết kế 6 panel chuẩn mực theo `config/dashboard.yaml` sử dụng nguồn dữ liệu `data/logs.jsonl`:
    1. *Latency percentiles & TTFT:* P50/P95/P99 latency và TTFT P95 (threshold P95 <= 3000ms).
    2. *Request traffic:* Lưu lượng request theo phút và request rate (threshold rate >= 1 req/min).
    3. *Error rate & retrieval success:* Tỷ lệ lỗi request (threshold <= 2%), breakdown theo `error_type`, và tỷ lệ thành công của retrieval (threshold >= 90%).
    4. *Cost over time:* Chi phí USD tích lũy theo phút và tổng toàn cửa sổ (threshold <= 2.5 USD).
    5. *Tokens in/out:* Tổng số tokens_in và tokens_out (threshold <= 50,000 tokens).
    6. *Quality proxy:* Điểm chất lượng trung bình của câu trả lời (threshold mean >= 0.75).
- **SLO và lý do chọn:**
  - Primary SLO: `fast_successful_requests` với mục tiêu 99.5% trong cửa sổ 28 ngày (`target_percent: 99.5%`).
  - Good event: `event == "response_sent" and latency_ms <= 3000` (request hoàn thành thành công trong thời gian dưới 3 giây).
  - Total event: `event == "request_received"`.
  - Lý do chọn: Thời gian phản hồi 3 giây là giới hạn chấp nhận được của người dùng khi trò chuyện với trợ lý AI (không gây cảm giác gián đoạn), và 99.5% phản ánh mục tiêu dịch vụ ổn định cao (High Availability).
- **Cách tính error budget:**
  - Error budget = `100% - Target SLO = 100% - 99.5% = 0.5%`.
  - Ví dụ: Trong cửa sổ 28 ngày nếu hệ thống có 100,000 request, lượng request chậm quá 3000ms hoặc thất bại tối đa được phép là `100,000 * 0.5% = 500 request`.
  - Khi số request lỗi vượt quá 500, Error Budget bị cạn kiệt, đội ngũ phát triển phải dừng release tính năng mới để tập trung xử lý độ trễ và độ tin cậy.
- **Ba alert và runbook tương ứng:**
  - Alert 1: `HighLatencyP95Breach` (Severity: warning, condition: `latency_p95 > 3000ms`, duration: `5m`). Kênh Slack `#llmops-alerts`. Runbook tại `docs/alerts.md#alert-1` hướng dẫn kiểm tra xem trễ ở khâu Retrieval hay Generation, lấy correlation ID để tra Langfuse trace waterfall.
  - Alert 2: `HighRequestErrorRate` (Severity: critical, condition: `error_rate_pct > 2.0%`, duration: `3m`). Kênh Slack `#llmops-alerts`. Runbook tại `docs/alerts.md#alert-2` hướng dẫn tra cứu `error_type` trong log, kiểm tra `/health` và kích hoạt circuit breaker/fallback.
  - Alert 3: `RetrievalSuccessRateDrop` (Severity: warning, condition: `retrieval_success_rate_pct < 90.0%`, duration: `5m`). Kênh Slack `#llmops-alerts`. Runbook tại `docs/alerts.md#alert-3` hướng dẫn kiểm tra kết nối vector store, tra cứu log `tool_success == false` và mở trace span retrieval để kiểm tra lỗi timeout.

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
