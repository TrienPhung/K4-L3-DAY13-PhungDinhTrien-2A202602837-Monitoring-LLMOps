# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Phùng Đình Triển
- **MSSV:** 2A202602837
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/TrienPhung/K4-L3-DAY13-PhungDinhTrien-2A202602837-Monitoring-LLMOps
- **Commit SHA cuối:** (điền ở CP4)
- **Challenge ID:** (điền ở CP3)
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602837`

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
| `validate_logs.py` | 30/100 (21 bản ghi, 20 thiếu trường bắt buộc, 0 correlation ID) | | |
| `validate_dashboard.py` | (chạy rồi điền) | | |
| `pytest` | 22 passed | | |
| Số traces hợp lệ | 10 (mới có span gốc `lab-agent-run`) | | |
| Số PII leak | 0 | | |
| Latency P95 / TTFT P95 | (điền sau khi tính) | | |
| Retrieval success rate | (điền sau khi tính) | | |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware đọc header `x-request-id`, nếu không có thì tự sinh `req-` cộng 8 ký tự hex, gắn vào structlog contextvars cho mọi dòng log của request, và trả lại qua header response.
- **Các metadata được ghi vào structured log:** `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`, cùng `latency_ms`, token, cost ở event `response_sent`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Bật `scrub_event` trong chuỗi processor, đặt trước `JsonlFileProcessor` (bước ghi file).
- **Cách kiểm chứng kết quả:** `validate_logs.py` đạt 100/100, `pytest` 26 passed, và ảnh 04, 05 (ID `req-aaaa0001` và `req-a1b2c3d4`).

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Key trong `.env` thuộc project `day13-k4-l3b-2A202602837`, ảnh 06 hiển thị tên project, khoảng thời gian và hơn 10 trace `day13-agent-request` sinh ra từ `load_test.py` và các request tôi tự gửi. Trace tôi đặt ID riêng (`req-aaaa0001`) tìm thấy đúng trong project này.
- **Cấu trúc root/retrieval/generation observations:** Root `lab-agent-run` (loại agent, trace name `day13-agent-request`) có hai observation con: `retrieval` (loại retriever, gắn `@observe` trên `retrieve()`) và `generation` (loại generation, gắn `@observe` trên `FakeLLM.generate()`). `generation` ghi `model`, `usage` (token vào/ra), `cost` và liên kết prompt version qua `propagate_attributes(prompt=...)`. Tất cả đặt `capture_input=False` và `capture_output=False` để không lưu nội dung câu hỏi (có thể chứa PII).
- **Cách nối trace với log:** `correlation_id` do middleware sinh được ghi vào metadata của trace (cùng với `feature`, `model`) và cũng có trong mọi dòng structured log. Ví dụ `req-aaaa0001` khớp giữa ảnh 04 và ảnh 08a.
- **Prompt name:** `day13-chat` (Text prompt, biến `{{feature}}`, `{{docs}}`, `{{message}}`).
- **Version/label baseline:** v1, nhãn `baseline` và `production`.
- **Version/label candidate:** v2 (thêm dòng "Answer briefly." ở cuối), nhãn `candidate` (nhãn `latest` do Langfuse tự gắn).
- **Trace ID của mỗi version:** v1: `6d1ffde5b412273958dad2422a98a42a` (`prompt_version=1`, `prompt_label=baseline`). v2: (điền trace ID sau khi chạy với label `candidate`, `prompt_version=2`).
- **Cách promote và rollback `production`:** Không sửa code, chỉ dời nhãn `production` trên giao diện Langfuse (Prompts → `day13-chat`). Promote: dời `production` từ v1 sang v2, đặt `LANGFUSE_PROMPT_LABEL=production`, restart API (app cache prompt khoảng 60 giây), gửi một request để kiểm tra `prompt_version=2` (ảnh 10a). Rollback: dời `production` về v1, restart API, gửi request kiểm tra `prompt_version=1` (ảnh 10b). Ảnh 09 thể hiện v1 (`baseline`, `production`) và v2 (`candidate`).

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard Streamlit đọc `data/logs.jsonl` theo `config/dashboard.yaml`, gồm 6 panel: Latency (P50/P95/P99, TTFT P95, ms), Traffic (requests/phút), Errors (error rate % và retrieval success %), Cost (USD), Tokens (vào/ra), Quality (điểm 0 đến 1). Mỗi panel có đơn vị, time range 60 phút, refresh 30 giây và đường threshold (ảnh 11).
- **SLO và lý do chọn:** 99.5% request hoàn thành thành công trong ≤ 3000 ms, cửa sổ 28 ngày. Baseline của tôi không có request lỗi, request thường mất 400-600 ms và chậm nhất khoảng 2.7 s (request khởi động), nên mục tiêu này đạt được nhưng vẫn phát hiện được sự cố retrieval chậm (+2.5 s).
- **Cách tính error budget:** SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn 3000 ms.
- **Ba alert và runbook tương ứng:** `HighLatencyP95` (P95 > 2000 ms trong 5 phút, cảnh báo sớm trước SLO), `HighErrorRate` (error rate > 2% hoặc retrieval success < 90% trong 5 phút), `HighCostPerRequest` (chi phí trung bình > 0.005 USD mỗi request trong 5 phút). Runbook nằm ở `docs/alerts.md` (Alert 1, 2, 3), theo chuỗi Metrics → Logs → Traces.

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

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
