import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import asyncio


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        async with self._lock:
            now = time.time()
            minute_ago = now - 60
            
            self.requests[client_ip] = [
                t for t in self.requests[client_ip] if t > minute_ago
            ]
            
            if len(self.requests[client_ip]) >= self.requests_per_minute:
                return Response(
                    content="Rate limit exceeded",
                    status_code=429,
                )
            
            self.requests[client_ip].append(now)
        
        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import logging
        logger = logging.getLogger(__name__)
        
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
        )
        
        return response
