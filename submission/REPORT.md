# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Ngô Tiến Dũng
- **MSSV:** 2A202602374
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/tiendungandrew-gif/K4-L3-DAY13-NgoTienDung-2A202602374-Monitoring-LLMOps
- **Commit SHA cuối:** `84b35f02019ee128fa1ff06e13da87de47e2312c`
- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1
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

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 16:07 – 16:12 (Asia/Ho_Chi_Minh) / 09:07:00Z – 09:12:00Z (UTC), ngày 29/09/2026.
- **Triệu chứng từ metrics:**
  - Panel Latency trên Dashboard ghi nhận Latency P95 tăng vọt từ ~155ms lên **2652ms** trên server, và client load test đo được độ trễ lên tới **10,627ms – 13,282ms** (khi chạy concurrency 5).
  - Vượt ngưỡng cảnh báo `latency_threshold_ms: 2000` của challenge config và vi phạm SLO 3000ms.
  - Trong khi đó, chỉ số TTFT P95 vẫn duy trì ở mức tối ưu **50ms**, và tỷ lệ lỗi không tăng (HTTP status code 200, Error rate = 0%). Điều này cho thấy tầng sinh văn bản của mô hình LLM vẫn hoạt động bình thường, độ trễ phát sinh hoàn toàn ở khâu tiền xử lý (pre-processing/retrieval).
- **Log line và correlation ID liên quan:**
  - Correlation ID: `req-8023b38d`
  - Dòng log `request_received`:
    ```json
    {"service": "api", "payload": {"message_preview": "Which signal should be checked after latency increases?"}, "event": "request_received", "correlation_id": "req-8023b38d", "user_id_hash": "4570299f37e2", "env": "dev", "session_id": "k4-l3a-challenge-s04", "feature": "monitoring", "model": "claude-sonnet-4-5", "level": "info", "ts": "2026-09-29T09:07:23.972706Z"}
    ```
  - Dòng log `response_sent`:
    ```json
    {"service": "api", "latency_ms": 2652, "ttft_ms": 50, "tokens_in": 36, "tokens_out": 93, "cost_usd": 0.001503, "quality_score": 0.9, "tool_name": "retrieval", "tool_success": true, "payload": {"answer_preview": "Starter answer. You should improve this output logic and add better quality chec..."}, "event": "response_sent", "correlation_id": "req-8023b38d", "user_id_hash": "4570299f37e2", "env": "dev", "session_id": "k4-l3a-challenge-s04", "feature": "monitoring", "model": "claude-sonnet-4-5", "level": "info", "ts": "2026-09-29T09:07:26.629394Z"}
    ```
- **Trace ID và span gây ảnh hưởng:**
  - Trace ID: `24701f61c6fa653c9e7a89d98c2f6ed2` (tìm kiếm bằng correlation_id `req-8023b38d` trên Langfuse)
  - Phân tích cây Trace Waterfall:
    - Root observation `lab-agent-run` (type `AGENT`): tổng thời gian 2.653s.
    - Child observation `retrieval` (type `RETRIEVER`): thời gian chạy **2.502s** (chiếm ~94.3% tổng thời gian request).
    - Child observation `fake-llm-generate` (type `GENERATION`): thời gian chạy chỉ **0.151s** (chiếm ~5.7%).
  - Kết luận: Span gây ảnh hưởng chính là `retrieval`.
- **Root cause:**
  - Sự cố `rag_slow` được inject vào hệ thống làm nghẽn bước truy xuất dữ liệu vector store (`retrieve()` trong `app/mock_rag.py`). Hàm này bị chèn độ trễ nhân tạo `time.sleep(2.5)`.
  - Khi có nhiều request gửi đồng thời (concurrency 5), việc các request đều bị nghẽn 2.5s tại khâu tìm kiếm tài liệu khiến hàng đợi bị dồn ứ, dẫn đến tổng thời gian chờ từ phía client tăng vọt lên hơn 10 - 13 giây.
- **Fix action:**
  - Về mặt xử lý sự cố tức thời: Tắt incident `rag_slow` qua lệnh `python scripts/inject_incident.py --disable` (gọi endpoint `/incidents/rag_slow/disable`).
  - Về mặt kỹ thuật hệ thống sản xuất:
    1. Kiểm tra tài nguyên và chỉ số IOPS/CPU của Vector Database.
    2. Tối ưu hóa cấu trúc chỉ mục tìm kiếm (chuyển sang HNSW hoặc IVF-PQ) và điều chỉnh giảm tham số `ef_search` hoặc `top_k`.
    3. Thêm Semantic Caching cho các truy vấn phổ biến để bỏ qua bước tra cứu lại đối với các câu hỏi tương tự.
    4. Thiết lập client timeout nghiêm ngặt (ví dụ: 1.5s) cho vector search kết hợp fallback về tra cứu từ khóa (BM25) hoặc sinh câu trả lời trực tiếp.
- **Preventive measure:**
  - Kích hoạt alert `HighLatencyP95Breach` (đã khai báo trong `config/alert_rules.yaml`) để gửi cảnh báo Slack ngay khi P95 > 3000ms kéo dài quá 5 phút.
  - Áp dụng kỹ thuật bất đồng bộ (async non-blocking I/O) khi gọi sang Vector DB.
  - Bổ sung circuit breaker để tự động cô lập vector store khi latency vượt ngưỡng và tự phục hồi khi hệ thống ổn định.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  - Thiết kế bộ lọc `scrub_event` đệ quy chạy trực tiếp trong pipeline của Structlog ngay trước processor ghi file JSONL (`JsonlFileProcessor`). Quyết định này bảo đảm mọi trường dữ liệu nhạy cảm (email, SĐT, CCCD, số thẻ thanh toán) ở bất kỳ độ sâu nào trong nested dictionaries/lists đều được làm sạch thành `[REDACTED_<TYPE>]` trước khi ghi xuống ổ đĩa, loại bỏ hoàn toàn nguy cơ rò rỉ dữ liệu PII ra log lưu trữ mà không làm phát sinh chi phí serialize lặp lại.
  - Đồng thời, thiết lập cơ chế đồng bộ hóa correlation ID chuẩn `req-<8-hex>` thông qua `CorrelationIdMiddleware` gắn vào cả Structlog contextvars và Langfuse trace metadata (`propagate_attributes`). Điều này tạo ra "sợi chỉ đỏ" duy nhất kết nối liền mạch từ log hệ thống sang APM tracing.
- **Một lỗi/blocker đã gặp:**
  - Trong quá trình triển khai CP2, ban đầu các trace trên Langfuse chỉ ghi nhận root observation mà thiếu các child observation phân cấp (`retrieval` và `fake-llm-generate`), khiến cho việc phân tích waterfall không tách biệt được thời gian tra cứu tài liệu với thời gian mô hình sinh câu trả lời.
  - Ngoài ra, regex mặc định ban đầu chưa xử lý triệt để CCCD 12 chữ số và các định dạng thẻ tín dụng có chứa khoảng trắng hoặc dấu gạch nối.
- **Cách tìm nguyên nhân và xử lý:**
  - Tra cứu cấu trúc trace trên Langfuse UI và đối chiếu với yêu cầu của `validate_logs.py` cùng hợp đồng phân cấp quan sát.
  - Xử lý bằng cách bổ sung decorator `@observe(name="retrieval", as_type="retriever")` trong `app/mock_rag.py` và `@observe(name="fake-llm-generate", as_type="generation")` trong `app/mock_llm.py`, gắn kèm `usage_details`, `cost_details`, `ttft_ms` và liên kết trực tiếp với Langfuse managed prompt.
  - Bổ sung biểu thức chính quy với word boundary `\b\d{12}\b` (CCCD) và `\b(?:\d{4}[ -]?){3}\d{4}\b` (Credit Card) trong `PII_PATTERNS`, viết thêm unit tests trong `tests/test_pii.py` và kiểm chứng đạt 24/24 tests pass.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - **Metrics (Triệu chứng vĩ mô):** Cung cấp góc nhìn tổng quan theo thời gian thực (Aggregated Real-time Health). Dashboard phát hiện P95 Latency tăng vọt vượt ngưỡng 3000ms hoặc Error Rate vượt 2% và kích hoạt cảnh báo (Alert) đến đội vận hành.
  - **Logs (Ngữ cảnh sự kiện):** Cung cấp chi tiết sự kiện tại thời điểm xảy ra sự cố. Từ khung giờ cảnh báo, kỹ sư tra cứu log trong `data/logs.jsonl` để lọc các request có `latency_ms` cao hoặc gặp lỗi, trích xuất `correlation_id` duy nhất (ví dụ: `req-8023b38d`).
  - **Traces (Bản đồ phân tích vi mô):** Sử dụng `correlation_id` làm khóa tìm kiếm trên Langfuse để mở Trace Waterfall tương ứng. Cây trace cho biết chính xác từng mili-giây tiêu tốn ở đâu (Root Agent: 2.65s, Retrieval: 2.50s, Generation: 0.15s), qua đó xác định trực tiếp điểm nghẽn nghẽn mạch (bottleneck) nằm tại bước truy xuất Vector Store mà không cần phỏng đoán.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - *Prompt Versioning & Rollback:* Tách biệt cấu hình prompt khỏi mã nguồn triển khai, cho phép đội ngũ LLMOps thử nghiệm prompt mới (candidate) một cách an toàn và rollback tức thì về phiên bản ổn định (`production`) ngay trên UI/API khi phát hiện suy giảm chất lượng câu trả lời hoặc bùng nổ độ trễ, mà không cần build lại Docker image hay restart dịch vụ.
  - *Token & Cost Monitoring:* Giám sát chặt chẽ ngân sách và phát hiện sớm các hiện tượng rò rỉ prompt, vòng lặp sinh token bất thường (infinite generation loops) hoặc tấn công làm cạn kiệt tài nguyên (denial of wallet).
  - *SLO & Error Budget:* Đặt ra ranh giới định lượng cụ thể giữa trải nghiệm người dùng (Latency P95 <= 3s, Availability >= 99.5%) và tốc độ phát triển sản phẩm; khi error budget bị tiêu hao nhanh, toàn bộ nguồn lực phải ưu tiên ổn định hạ tầng thay vì deploy tính năng mới.
- **Điều quan trọng nhất đã học:**
  - Xây dựng hệ thống LLMOps production-ready đòi hỏi phương pháp tiếp cận toàn diện (Full-stack Observability), nơi Structured Logging chuẩn JSON schema, Context Enrichment, tự động hóa lọc PII và Distributed Tracing phải phối hợp chặt chẽ với nhau để bảo đảm cả tính minh bạch hoạt động (operational transparency), độ tin cậy và sự tuân thủ nghiêm ngặt về quyền riêng tư dữ liệu.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**
  - Bài lab hiện sử dụng mock RAG và mock LLM để kiểm thử luồng quan sát; trong môi trường sản xuất quy mô lớn, cần tích hợp thêm Semantic Caching (Redis/Qdrant cache) để giảm thiểu chi phí cho các câu hỏi trùng lặp, và cấu hình Circuit Breaker tự động cô lập dịch vụ LLM bên thứ ba khi API nhà cung cấp gặp sự cố hoặc timeout kéo dài.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
