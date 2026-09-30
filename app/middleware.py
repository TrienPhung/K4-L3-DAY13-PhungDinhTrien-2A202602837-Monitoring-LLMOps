from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Xoá context của request trước để không bị lẫn dữ liệu
        clear_contextvars()

        # Lấy x-request-id từ header, nếu không có thì tự sinh req-<8 ký tự hex>
        correlation_id = request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:8]}"

        # Gắn vào mọi dòng log của request này
        bind_contextvars(correlation_id=correlation_id)

        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        response = await call_next(request)

        # Trả ID và thời gian xử lý về cho client
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = str(int((time.perf_counter() - start) * 1000))

        return response