# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: SLO `fast_successful_requests` (99.5% request hoàn thành ≤ 3000 ms trong 28 ngày); SLI là `latency_ms` của event `response_sent`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 2000ms` liên tục 5 phút. Đây là cảnh báo sớm, trước ngưỡng SLO 3000 ms (request bình thường mất 400-600 ms)
- Ảnh hưởng tới người dùng: người dùng chờ lâu hơn để nhận câu trả lời; nếu kéo dài sẽ tiêu hao error budget 0.5%
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel Latency, xác nhận P50/P95/P99 và khoảng thời gian tăng (dashboard dùng giờ UTC).
  2. Lọc `data/logs.jsonl` trong khoảng đó và lấy một `correlation_id` có `latency_ms` cao: `python -c "import json; [print(r['ts'], r.get('correlation_id'), r['latency_ms']) for r in map(json.loads, open('data/logs.jsonl', encoding='utf-8')) if r.get('latency_ms', 0) > 2000]"`
  3. Mở trace cùng `correlation_id` trên Langfuse (giờ Việt Nam, lệch +7 giờ so với log), so sánh span `retrieval` và `generation` để xác định bước nào chậm.
- Mitigation tạm thời: nếu đang chạy kịch bản thực hành thì tắt bằng `python scripts/inject_incident.py --scenario rag_slow --disable`; khôi phục cấu hình retrieval; rollback prompt `production` về v1 nếu span `generation` chậm sau khi đổi prompt; giảm tải khi demo
- Owner: `student-2A202602837`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: SLO `fast_successful_requests` (request phải thành công), guardrail `error_rate_pct_max: 2` và `retrieval_success_rate_pct_min: 90`
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` hoặc `retrieval_success_rate_pct < 90` liên tục 5 phút
- Ảnh hưởng tới người dùng: người dùng nhận lỗi HTTP 500 và không có câu trả lời; error budget bị tiêu hao rất nhanh
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel Errors, xác nhận Error rate % tăng và Retrieval success % giảm, cùng khoảng thời gian.
  2. Lọc `data/logs.jsonl` các dòng `event == "request_failed"`, đọc `error_type`, `tool_success` và lấy `correlation_id` của một request lỗi.
  3. Mở trace cùng `correlation_id` trên Langfuse, kiểm tra span `retrieval` có trạng thái lỗi hay không và lỗi xảy ra ở bước nào.
- Mitigation tạm thời: khôi phục nguồn retrieval (vector store); nếu đang chạy kịch bản thực hành thì tắt bằng `python scripts/inject_incident.py --scenario tool_fail --disable`; thêm retry hoặc câu trả lời dự phòng khi retrieval lỗi
- Owner: `student-2A202602837`

## Alert 3

- Tên: `HighCostPerRequest`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: guardrail `daily_cost_usd_max: 2.5`; SLI là `cost_usd` và `tokens_out` của event `response_sent`
- Điều kiện và thời gian duy trì: `avg(cost_usd) > 0.005 USD` mỗi request liên tục 5 phút (baseline khoảng 0.002 USD), hoặc tổng chi phí trong ngày vượt 2.5 USD
- Ảnh hưởng tới người dùng: người dùng chưa thấy lỗi ngay, nhưng chi phí vận hành tăng nhanh và có nguy cơ vượt ngân sách, buộc phải giới hạn dịch vụ
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel Cost và Tokens, xác nhận chi phí và `tokens_out` tăng bất thường so với baseline.
  2. Lọc `data/logs.jsonl` các dòng `response_sent` có `tokens_out` hoặc `cost_usd` cao và lấy một `correlation_id`.
  3. Mở trace cùng `correlation_id` trên Langfuse, xem observation `generation` (token, cost) và `prompt_version` đang dùng.
- Mitigation tạm thời: rollback prompt `production` về phiên bản trước; giới hạn số token đầu ra; nếu đang chạy kịch bản thực hành thì tắt bằng `python scripts/inject_incident.py --scenario cost_spike --disable`
- Owner: `student-2A202602837`