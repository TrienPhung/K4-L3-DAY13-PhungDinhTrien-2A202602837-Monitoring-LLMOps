# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Phùng Đình Triển
- **MSSV:** 2A202602837
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/TrienPhung/K4-L3-DAY13-PhungDinhTrien-2A202602837-Monitoring-LLMOps
- **Commit SHA cuối:** (điền ở CP4)
- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602837`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08a-trace-metadata.png`, `evidence/08b-generation.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10a-prompt-promote.png`, `evidence/10b-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 (21 bản ghi, 20 thiếu trường bắt buộc, 0 correlation ID) | 100/100 (10 correlation ID, 0 thiếu trường, 0 PII leak) | Đạt sau khi thêm correlation ID, enrichment và bật `scrub_event` |
| `validate_dashboard.py` | Chưa chạy (chưa có dashboard) | 6/6 panel hợp lệ | Dashboard Streamlit đủ 6 panel, có threshold |
| `pytest` | 22 passed | 26 passed | Thêm 4 test PII (CCCD, thẻ, hỗn hợp, văn bản thường) |
| Số traces hợp lệ | 10 (mới có span gốc `lab-agent-run`) | Hơn 10 trace có cây span `retrieval` + `generation` | Ảnh 06, 07 |
| Số PII leak | 0 | 0 | Log chỉ còn nhãn `[REDACTED_*]` |
| Latency P95 / TTFT P95 | Chưa đo (chưa có dashboard) | P95 1473 ms / TTFT P95 50 ms | Dưới ngưỡng SLO 3000 ms (số từ dashboard, ảnh 11) |
| Retrieval success rate | Chưa đo (chưa có dashboard) | 100% | Trên guardrail 90% |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware đọc header `x-request-id`, nếu không có thì tự sinh `req-` cộng 8 ký tự hex, gắn vào structlog contextvars cho mọi dòng log của request, và trả lại qua header response.
- **Các metadata được ghi vào structured log:** `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`, cùng `latency_ms`, token, cost ở event `response_sent`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Bật `scrub_event` trong chuỗi processor, đặt trước `JsonlFileProcessor` (bước ghi file).
- **Cách kiểm chứng kết quả:** `validate_logs.py` đạt 100/100, `pytest` 26 passed, và ảnh 04, 05 (ID `req-aaaa0001` và `req-a1b2c3d4`).

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Key trong `.env` thuộc project `day13-k4-l3b-2A202602837`, ảnh 06 hiển thị tên project, khoảng thời gian và hơn 10 trace `day13-agent-request` sinh ra từ `load_test.py` và các request tôi tự gửi. Trace tôi đặt ID riêng (`req-aaaa0001`) tìm thấy đúng trong project này.
- **Cấu trúc root/retrieval/generation observations:** Root `lab-agent-run` (loại agent, trace name `day13-agent-request`) có hai observation con: `retrieval` (loại retriever, gắn `@observe` trên `retrieve()`) và `generation` (loại generation, gắn `@observe` trên `FakeLLM.generate()`). `generation` ghi `model`, `usage` (token vào/ra), `cost` và liên kết prompt version qua `propagate_attributes(prompt=...)`. Tất cả đặt `capture_input=False` và `capture_output=False` để không lưu nội dung câu hỏi (có thể chứa PII).
- **Cách nối trace với log:** `correlation_id` do middleware sinh được ghi vào metadata của trace (cùng với `feature`, `model`) và cũng có trong mọi dòng structured log. Ví dụ `req-aaaa0001` khớp giữa ảnh 04 và ảnh 08a (do đặt lại cùng ID nhiều lần nên các trace được phân biệt bằng trace ID và giờ).
- **Prompt name:** `day13-chat` (Text prompt, biến `{{feature}}`, `{{docs}}`, `{{message}}`).
- **Version/label baseline:** v1, nhãn `baseline` và `production`.
- **Version/label candidate:** v2 (thêm dòng "Answer briefly." ở cuối), nhãn `candidate` (nhãn `latest` do Langfuse tự gắn).
- **Trace ID của mỗi version:** v1: `18dda823f619f3557615ca84a512d82c` (prompt_version=1, label production, correlation_id req-aaaa0001). v2: `250180fba949fa50673d2c88ad9442a9` (prompt_version=2, label candidate, correlation_id req-bbbb0002).
- **Cách promote và rollback `production`:** Không sửa code, chỉ dời nhãn `production` trên giao diện Langfuse (Prompts → `day13-chat`). Promote: dời `production` từ v1 sang v2 (ảnh 10a). Rollback: dời `production` về v1 (ảnh 10b). Vì app cache prompt khoảng 60 giây, sau mỗi lần đổi nhãn phải restart API rồi mới gửi request. Ảnh 09 thể hiện v1 (`baseline`, `production`) và v2 (`candidate`).

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard Streamlit đọc `data/logs.jsonl` theo `config/dashboard.yaml`, gồm 6 panel: Latency (P50/P95/P99, TTFT P95, ms), Traffic (requests/phút), Errors (error rate % và retrieval success %), Cost (USD), Tokens (vào/ra), Quality (điểm 0 đến 1). Mỗi panel có đơn vị, time range 60 phút, refresh 30 giây và đường threshold (ảnh 11).
- **SLO và lý do chọn:** 99.5% request hoàn thành thành công trong ≤ 3000 ms, cửa sổ 28 ngày. Baseline của tôi không có request lỗi, request thường mất 400-600 ms; chỉ request đầu tiên sau khi restart API chậm hơn (2.7 đến 4.6 s) vì phải tải prompt. Những request này tính vào error budget, nên mục tiêu 99.5% vẫn đạt được nhưng có ý nghĩa, và sự cố retrieval chậm (+2.5 s) vẫn phát hiện được.
- **Cách tính error budget:** SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn 3000 ms.
- **Ba alert và runbook tương ứng:** `HighLatencyP95` (P95 > 2000 ms trong 5 phút, cảnh báo sớm trước SLO), `HighErrorRate` (error rate > 2% hoặc retrieval success < 90% trong 5 phút), `HighCostPerRequest` (chi phí trung bình > 0.005 USD mỗi request trong 5 phút). Runbook nằm ở `docs/alerts.md` (Alert 1, 2, 3), theo chuỗi Metrics → Logs → Traces.

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Khoảng thời gian điều tra:** 14:42 UTC – 14:44 UTC (tức 21:42 – 21:44 GMT+7, ngày 30/09/2026)
- **Triệu chứng từ metrics:** Panel Latency percentiles and TTFT ghi nhận P95 vọt từ baseline 615 ms (P50 153 ms) lên 2655 ms (P99 đạt 2656 ms), vượt ngưỡng cảnh báo 2000 ms của alert `HighLatencyP95`. TTFT P95 duy trì ổn định ở mức 50 ms, cho thấy thời gian sinh token đầu tiên không bị ảnh hưởng mà độ trễ bị cộng dồn ở giai đoạn xử lý trước đó. Panel Traffic ghi nhận 5 requests concurrent cho feature `monitoring`. Panel Errors có Error rate 0%, Retrieval success rate 100%.
- **Log line và correlation ID liên quan:** Lọc `data/logs.jsonl` tại thời điểm sự cố (14:43 UTC), chọn request đại diện có `correlation_id: req-ba2468e1` (thuộc batch 5 request `req-ba2468e1`, `req-c54f78fb`, `req-f5d73298`, `req-e93bc5b8`, `req-4ca623bc`). Dòng log `response_sent`:
  ```json
  {"service": "api", "latency_ms": 2653, "ttft_ms": 50, "tokens_in": 35, "tokens_out": 153, "cost_usd": 0.0024, "quality_score": 0.8, "tool_name": "retrieval", "tool_success": true, "payload": {"answer_preview": "Starter answer. You should improve this output logic and add better quality chec..."}, "event": "response_sent", "feature": "monitoring", "model": "claude-sonnet-4-5", "user_id_hash": "4a1a454d70a9", "correlation_id": "req-ba2468e1", "session_id": "k4-l3b-challenge-s01", "env": "dev", "level": "info", "ts": "2026-09-30T14:43:33.576431Z"}
  ```
  `latency_ms` đạt 2653 ms (tăng vọt ~2500 ms so với mức baseline thông thường ~150–165 ms).
- **Trace ID và span gây ảnh hưởng:** Trace ID `a95f854abeb34bddd71fd2c24d4f2ce2` trên Langfuse cá nhân (khớp `correlation_id: req-ba2468e1`, session `k4-l3b-challenge-s01`). Cấu trúc span:
  - Root observation: `lab-agent-run` (type: AGENT) tổng thời gian 2.653s (2653 ms).
  - Span con gây ảnh hưởng: `retrieval` (type: RETRIEVER) chiếm tới 2.501s (2501 ms, tức ~94% tổng latency của trace).
  - Span con `generation` (type: GENERATION) chỉ mất 152 ms, hoàn toàn bình thường.
  => Span trực tiếp gây nghẽn và làm chậm hệ thống là span `retrieval`.
- **Root cause:** Kịch bản incident `rag_slow` được kích hoạt (`STATE["rag_slow"] = True`), dẫn đến việc thực thi lệnh `time.sleep(2.5)` (2.5 giây) trong hàm `retrieve()` của file `app/mock_rag.py` khi truy xuất tài liệu cho feature `monitoring`, mô phỏng sự cố vector store hoặc retriever bên ngoài bị suy giảm hiệu năng.
- **Fix action:** Tắt ngay incident `rag_slow` trên hệ thống thông qua endpoint điều khiển: gửi request `POST /incidents/rag_slow/disable` (chạy script `python scripts/inject_incident.py --disable`), đưa cờ `rag_slow` về `False`. Sau khi tắt, request phục hồi về mức latency baseline bình thường (~160 ms).
- **Preventive measure:**
  1. Thêm cơ chế timeout và fallback cho retriever: bọc lệnh gọi vector store với timeout tối đa 1500 ms; nếu quá thời gian thì tự động fallback sang context dự phòng hoặc trả lời bằng tri thức nội tại của model kèm cảnh báo.
  2. Bật và giám sát alert `HighLatencyP95` (P95 > 2000 ms liên tục 5 phút) để phát hiện sớm và kích hoạt runbook trước khi vi phạm ngưỡng SLO 3000 ms.
  3. Xây dựng synthetic check / probe định kỳ độc lập để kiểm tra latency của dịch vụ retrieval, kịp thời phát hiện vector store bị chậm trước khi ảnh hưởng đến người dùng thực tế.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Đặt processor `scrub_event` ngay trước `JsonlFileProcessor` trong pipeline logging của structlog và cấu hình `capture_input=False`, `capture_output=False` trên các decorator `@observe` của Langfuse. Quyết định này nhằm bảo đảm nguyên tắc bảo mật và quyền riêng tư (Zero PII Leakage) ở cả hai tầng quan sát: log cục bộ loại bỏ hoàn toàn số CCCD, số thẻ tín dụng, số điện thoại; đồng thời trace đẩy lên nền tảng SaaS bên ngoài (Langfuse Cloud) không chứa dữ liệu thô của người dùng.
- **Một lỗi/blocker đã gặp:** Trong quá trình thực hiện CP2, sau khi promote prompt `production` từ v1 lên v2 trên giao diện Langfuse, request gửi vào API ngay sau đó vẫn sử dụng prompt version 1 cũ mà chưa cập nhật version 2.
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra code tại `app/prompt_management.py` và phát hiện biến `_CACHE` lưu cache prompt trong bộ nhớ tiến trình (TTL 60 giây). Do đó, sau khi cập nhật nhãn trên Langfuse UI, cần restart server API (hoặc chờ hết TTL) để ứng dụng xóa cache và tải lại prompt mới nhất từ Langfuse.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - *Metrics*: Đóng vai trò cảnh báo sớm ("What is wrong?"), cung cấp bức tranh vĩ mô (P95 latency tăng, error rate tăng) và kích hoạt alert/runbook khi chạm ngưỡng cảnh báo.
  - *Logs*: Đóng vai trò khoanh vùng đối tượng ("Where and who is affected?"), cung cấp chi tiết từng sự kiện, timestamp và `correlation_id` của các request cụ thể bị ảnh hưởng.
  - *Traces*: Đóng vai trò định vị nguyên nhân gốc rễ ("Why did it happen?"), soi chiếu sâu vào cây span (retrieval vs generation) của đúng `correlation_id` đó để chỉ ra chính xác span nào tiêu tốn thời gian hoặc phát sinh lỗi.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - *Prompt version & rollback*: Cho phép quản lý sự thay đổi prompt có hệ thống như mã nguồn, tách biệt chu kỳ release prompt khỏi release code, cho phép rollback tức thì khi prompt mới làm suy giảm chất lượng hoặc tăng chi phí mà không cần redeploy.
  - *Token & Cost*: Chi phí LLM tỉ lệ thuận với lượng token vào/ra; nếu không có guardrail và giám sát chặt chẽ, các prompt dài hoặc vòng lặp sinh token có thể gây bùng nổ chi phí (cost spike).
  - *SLO & Error Budget*: Đặt ra ranh giới định lượng giữa độ tin cậy dịch vụ và tốc độ thử nghiệm tính năng mới. Error budget (0.5%) giúp đội ngũ biết khi nào an toàn để deploy và khi nào cần dừng để ổn định hệ thống.
- **Điều quan trọng nhất đã học:** Khả năng liên kết xuyên suốt ba trụ cột Observability (Metrics, Logs, Traces) thông qua `correlation_id` duy nhất và quy trình điều tra sự cố chuẩn mực, không đoán mò root cause mà luôn đối chiếu bằng chứng nhất quán từ metric đến log và trace.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Các panel dashboard hiện tại đọc trực tiếp từ file log cục bộ (`data/logs.jsonl`) qua Streamlit trong cửa sổ trượt 60 phút, chưa tích hợp hệ thống time-series database chuyên dụng phân tán (như Prometheus, Grafana, OpenTelemetry Collector) cho môi trường production quy mô lớn.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.