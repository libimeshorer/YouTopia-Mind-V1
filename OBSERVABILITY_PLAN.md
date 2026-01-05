# Centralized Logging & Observability Implementation Plan

## Overview

This plan establishes production-grade observability for YouTopia Mind across all platforms (Render, Vercel, AWS Lambda, Pinecone). The implementation is divided into 3 phases, prioritized by impact and urgency.

---

## Phase 1: Minimum Viable Observability (Critical - Do First)

**Goal**: Catch errors, aggregate logs, and get alerted before users complain.

### 1.1 Add Sentry for Error Tracking

**Why**: Instant visibility into all exceptions across frontend and backend with stack traces, user context, and release tracking.

**Backend Changes**:

#### 1.1.1 Install Sentry SDK
```
# Add to requirements.txt
sentry-sdk[fastapi]>=1.39.0
```

#### 1.1.2 Create Sentry configuration module
**File**: `src/utils/sentry.py`
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import structlog
import os

def init_sentry():
    """Initialize Sentry error tracking"""
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")

    if not sentry_dsn:
        structlog.get_logger().warning("SENTRY_DSN not set, error tracking disabled")
        return

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            HttpxIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        traces_sample_rate=0.1 if environment == "production" else 1.0,
        profiles_sample_rate=0.1 if environment == "production" else 1.0,
        send_default_pii=False,  # GDPR compliance
        before_send=filter_sensitive_data,
    )

def filter_sensitive_data(event, hint):
    """Remove sensitive data before sending to Sentry"""
    # Filter out authentication tokens, passwords, etc.
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        if "authorization" in headers:
            headers["authorization"] = "[FILTERED]"
    return event

def set_user_context(user_id: str, tenant_id: str = None):
    """Set user context for Sentry error reports"""
    sentry_sdk.set_user({
        "id": user_id,
        "tenant_id": tenant_id,
    })

def capture_message(message: str, level: str = "info", extras: dict = None):
    """Capture a custom message in Sentry"""
    with sentry_sdk.push_scope() as scope:
        if extras:
            for key, value in extras.items():
                scope.set_extra(key, value)
        sentry_sdk.capture_message(message, level=level)
```

#### 1.1.3 Initialize in server.py
**File**: `src/api/server.py` - Add to startup
```python
from src.utils.sentry import init_sentry

# Call before app creation
init_sentry()
```

#### 1.1.4 Update exception handlers to capture in Sentry
**File**: `src/api/server.py` - Modify exception handlers
```python
import sentry_sdk

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with Sentry capture"""
    # Sentry auto-captures, but we add context
    sentry_sdk.set_context("request", {
        "path": request.url.path,
        "method": request.method,
        "query_params": str(request.query_params),
    })

    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    # ... rest of handler
```

**Frontend Changes**:

#### 1.1.5 Install Sentry React SDK
```bash
# Add to frontend/package.json
npm install @sentry/react @sentry/vite-plugin
```

#### 1.1.6 Create Sentry configuration
**File**: `frontend/src/lib/sentry.ts`
```typescript
import * as Sentry from "@sentry/react";

export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;

  if (!dsn) {
    console.warn("VITE_SENTRY_DSN not set, error tracking disabled");
    return;
  }

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    tracesSampleRate: import.meta.env.MODE === "production" ? 0.1 : 1.0,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
  });
}

export function setUserContext(userId: string, tenantId?: string) {
  Sentry.setUser({
    id: userId,
    tenant_id: tenantId,
  });
}

export function captureException(error: Error, context?: Record<string, unknown>) {
  Sentry.captureException(error, { extra: context });
}
```

#### 1.1.7 Initialize in main.tsx
**File**: `frontend/src/main.tsx`
```typescript
import { initSentry } from "./lib/sentry";
initSentry();
// ... rest of app
```

#### 1.1.8 Wrap App with Sentry Error Boundary
**File**: `frontend/src/App.tsx`
```typescript
import * as Sentry from "@sentry/react";

// Wrap router with error boundary
<Sentry.ErrorBoundary fallback={<ErrorFallback />}>
  <RouterProvider router={router} />
</Sentry.ErrorBoundary>
```

**Environment Variables Required**:
```
# Backend (.env)
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# Frontend (.env)
VITE_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

---

### 1.2 Add Request ID Tracing

**Why**: Correlate logs across frontend → backend → external services for debugging.

#### 1.2.1 Create request context middleware
**File**: `src/middleware/request_context.py`
```python
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import sentry_sdk

class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request ID and timing to all requests"""

    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        # Set Sentry tag
        sentry_sdk.set_tag("request_id", request_id)

        # Process request
        import time
        start_time = time.perf_counter()

        response = await call_next(request)

        # Log request completion
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger = structlog.get_logger()
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
```

#### 1.2.2 Add middleware to server.py
**File**: `src/api/server.py`
```python
from src.middleware.request_context import RequestContextMiddleware

# Add after CORS middleware
app.add_middleware(RequestContextMiddleware)
```

#### 1.2.3 Update frontend API client to pass request ID
**File**: `frontend/src/api/client.ts`
```typescript
// Add to request interceptor
const requestId = crypto.randomUUID();
config.headers["X-Request-ID"] = requestId;
console.info(`[${requestId}] ${config.method?.toUpperCase()} ${config.url}`);
```

---

### 1.3 Set Up Log Aggregation (Better Stack / Logtail)

**Why**: All logs in one searchable place with 30-day retention (free tier).

**Recommendation**: Better Stack (formerly Logtail) - integrates well with Python structlog and has a generous free tier.

#### 1.3.1 Install logtail-python
```
# Add to requirements.txt
logtail-python>=0.2.0
```

#### 1.3.2 Update logging configuration
**File**: `src/utils/logging.py`
```python
import logging
import sys
import os
import structlog
from structlog.stdlib import LoggerFactory

def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured logging with optional Logtail export"""

    # Base processors for structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Configure output based on environment
    environment = os.getenv("ENVIRONMENT", "development")
    logtail_token = os.getenv("LOGTAIL_SOURCE_TOKEN")

    if logtail_token and environment == "production":
        # Production: JSON format for log aggregation
        from logtail import LogtailHandler

        # Add JSON processor for structured output
        processors.append(structlog.processors.JSONRenderer())

        # Configure Logtail handler
        logtail_handler = LogtailHandler(source_token=logtail_token)

        logging.basicConfig(
            format="%(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logtail_handler,
            ],
            level=getattr(logging, log_level.upper()),
        )
    else:
        # Development: Human-readable console output
        processors.append(structlog.dev.ConsoleRenderer())

        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, log_level.upper()),
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

#### 1.3.3 Vercel Frontend Log Forwarding
For Vercel, use their Log Drains feature (Pro plan required) or use Sentry for frontend errors.

**Alternative for free tier**: Use Sentry's breadcrumbs feature which captures console logs leading up to errors.

---

### 1.4 Add Health Check Enhancements

**Why**: Current health check only confirms server is running, not that dependencies are healthy.

#### 1.4.1 Create comprehensive health check
**File**: `src/api/routers/health.py`
```python
from fastapi import APIRouter, Response
from src.utils.logging import get_logger
from src.config.settings import settings
import httpx
import asyncio

router = APIRouter()
logger = get_logger(__name__)

@router.get("/health")
async def basic_health():
    """Basic health check - always fast"""
    return {"status": "healthy", "service": "youtopia-mind-api"}

@router.get("/health/ready")
async def readiness_check():
    """Check if all dependencies are ready"""
    checks = {}
    overall_healthy = True

    # Check database
    try:
        from src.db.database import get_db
        # Quick query to test connection
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # Check Pinecone
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(settings.pinecone_index_name)
        stats = index.describe_index_stats()
        checks["pinecone"] = {
            "status": "healthy",
            "vector_count": stats.total_vector_count,
        }
    except Exception as e:
        checks["pinecone"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # Check OpenAI (quick models list call)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                timeout=5.0,
            )
            resp.raise_for_status()
            checks["openai"] = {"status": "healthy"}
    except Exception as e:
        checks["openai"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    status_code = 200 if overall_healthy else 503
    return Response(
        content=json.dumps({
            "status": "healthy" if overall_healthy else "unhealthy",
            "checks": checks,
        }),
        status_code=status_code,
        media_type="application/json",
    )
```

#### 1.4.2 Add router to server.py
```python
from src.api.routers import health
app.include_router(health.router, tags=["health"])
```

---

### 1.5 Set Up External Uptime Monitoring

**Why**: Know when your service is down before users tell you.

**Recommended**: UptimeRobot (free tier: 50 monitors, 5-min intervals)

**Configuration**:
1. Monitor `GET https://your-api.onrender.com/health`
2. Monitor `GET https://your-api.onrender.com/health/ready` (less frequent, e.g., 15 min)
3. Set up Slack/email alerts for downtime

---

## Phase 2: Performance & Debugging Visibility

**Goal**: Understand latency, identify bottlenecks, debug slow requests.

### 2.1 Add Performance Metrics

#### 2.1.1 Install Prometheus client
```
# Add to requirements.txt
prometheus-client>=0.19.0
prometheus-fastapi-instrumentator>=6.1.0
```

#### 2.1.2 Add Prometheus instrumentation
**File**: `src/api/server.py`
```python
from prometheus_fastapi_instrumentator import Instrumentator

# After app creation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

#### 2.1.3 Add custom metrics for critical paths
**File**: `src/utils/metrics.py`
```python
from prometheus_client import Histogram, Counter

# LLM metrics
LLM_REQUEST_DURATION = Histogram(
    "llm_request_duration_seconds",
    "Time spent on LLM API calls",
    ["model", "operation"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

LLM_TOKEN_USAGE = Counter(
    "llm_tokens_total",
    "Total tokens used",
    ["model", "type"],  # type: prompt, completion
)

# RAG metrics
RAG_RETRIEVAL_DURATION = Histogram(
    "rag_retrieval_duration_seconds",
    "Time spent on RAG retrieval",
    ["index"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5],
)

RAG_CHUNKS_RETRIEVED = Histogram(
    "rag_chunks_retrieved",
    "Number of chunks retrieved per query",
    ["index"],
    buckets=[1, 3, 5, 10, 20],
)

# Document processing
DOCUMENT_PROCESSING_DURATION = Histogram(
    "document_processing_duration_seconds",
    "Time to process uploaded documents",
    ["file_type"],
    buckets=[1, 5, 10, 30, 60, 120],
)
```

#### 2.1.4 Instrument LLM client
**File**: `src/llm/client.py` - Add timing
```python
from src.utils.metrics import LLM_REQUEST_DURATION, LLM_TOKEN_USAGE
import time

async def generate_response(self, messages, model="gpt-4-turbo-preview"):
    start_time = time.perf_counter()
    try:
        response = await self._call_openai(messages, model)

        # Record metrics
        duration = time.perf_counter() - start_time
        LLM_REQUEST_DURATION.labels(model=model, operation="chat").observe(duration)

        if response.usage:
            LLM_TOKEN_USAGE.labels(model=model, type="prompt").inc(response.usage.prompt_tokens)
            LLM_TOKEN_USAGE.labels(model=model, type="completion").inc(response.usage.completion_tokens)

        return response
    except Exception as e:
        LLM_REQUEST_DURATION.labels(model=model, operation="chat_error").observe(
            time.perf_counter() - start_time
        )
        raise
```

---

### 2.2 Add Distributed Tracing with OpenTelemetry

**Why**: See the full journey of a request across services.

#### 2.2.1 Install OpenTelemetry
```
# Add to requirements.txt
opentelemetry-api>=1.22.0
opentelemetry-sdk>=1.22.0
opentelemetry-instrumentation-fastapi>=0.43b0
opentelemetry-instrumentation-httpx>=0.43b0
opentelemetry-instrumentation-sqlalchemy>=0.43b0
opentelemetry-exporter-otlp>=1.22.0
```

#### 2.2.2 Create tracing configuration
**File**: `src/utils/tracing.py`
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
import os

def init_tracing(app, db_engine):
    """Initialize OpenTelemetry tracing"""
    otlp_endpoint = os.getenv("OTLP_ENDPOINT")

    if not otlp_endpoint:
        return

    # Create resource with service info
    resource = Resource.create({
        "service.name": "youtopia-mind-api",
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    # Configure tracer provider
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument frameworks
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engine=db_engine)
```

---

### 2.3 Add Structured Frontend Logging

**Why**: Replace console.log chaos with structured, filterable logs.

#### 2.3.1 Install pino for browser
```bash
npm install pino pino-pretty
```

#### 2.3.2 Create logger utility
**File**: `frontend/src/lib/logger.ts`
```typescript
type LogLevel = "debug" | "info" | "warn" | "error";

interface LogContext {
  [key: string]: unknown;
}

class Logger {
  private context: LogContext = {};

  child(context: LogContext): Logger {
    const child = new Logger();
    child.context = { ...this.context, ...context };
    return child;
  }

  private log(level: LogLevel, message: string, data?: LogContext) {
    const entry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      ...this.context,
      ...data,
    };

    // In development, pretty print
    if (import.meta.env.DEV) {
      const color = {
        debug: "color: gray",
        info: "color: blue",
        warn: "color: orange",
        error: "color: red",
      }[level];
      console.log(`%c[${level.toUpperCase()}] ${message}`, color, data || "");
    } else {
      // In production, structured JSON for log aggregation
      console[level](JSON.stringify(entry));
    }

    // Also send errors to Sentry
    if (level === "error" && data?.error instanceof Error) {
      import("@sentry/react").then((Sentry) => {
        Sentry.captureException(data.error, { extra: entry });
      });
    }
  }

  debug(message: string, data?: LogContext) {
    this.log("debug", message, data);
  }
  info(message: string, data?: LogContext) {
    this.log("info", message, data);
  }
  warn(message: string, data?: LogContext) {
    this.log("warn", message, data);
  }
  error(message: string, data?: LogContext) {
    this.log("error", message, data);
  }
}

export const logger = new Logger();
```

#### 2.3.3 Update API client to use structured logging
**File**: `frontend/src/api/client.ts`
```typescript
import { logger } from "@/lib/logger";

const apiLogger = logger.child({ component: "api-client" });

// Replace console.log with structured logging
apiLogger.info("Request started", { method, url, requestId });
apiLogger.info("Response received", { status, duration, requestId });
apiLogger.error("Request failed", { error, url, requestId });
```

---

## Phase 3: Advanced Observability (Scale-Ready)

**Goal**: Full production observability with dashboards, SLOs, and alerting.

### 3.1 Centralized Observability Platform

**Recommended Options**:

| Platform | Pros | Cons | Cost |
|----------|------|------|------|
| **Datadog** | All-in-one, excellent UX | Expensive at scale | ~$15/host/mo |
| **Grafana Cloud** | Open source friendly, flexible | More setup | Free tier generous |
| **New Relic** | Good APM, easy setup | Can get expensive | Free tier available |

**Recommendation for YouTopia Mind**: Start with **Grafana Cloud** free tier
- 10k metrics, 50GB logs, 50GB traces/month free
- Can self-host later if needed
- Works well with Prometheus metrics already added

### 3.2 Create Observability Dashboards

#### 3.2.1 Key Dashboard Panels

**API Health Dashboard**:
- Request rate (requests/second)
- Error rate (4xx, 5xx percentage)
- Latency percentiles (p50, p95, p99)
- Active sessions

**LLM Performance Dashboard**:
- Token usage over time (cost tracking)
- LLM latency distribution
- Error rate by model
- Retry frequency

**RAG Performance Dashboard**:
- Retrieval latency
- Chunks retrieved per query
- Cache hit rate (if implemented)
- Index size over time

**Document Processing Dashboard**:
- Documents processed per hour
- Processing duration by file type
- Error rate by file type
- Queue depth (if applicable)

### 3.3 Set Up Alerting Rules

#### 3.3.1 Critical Alerts (Page immediately)
```yaml
# Example Prometheus alerting rules
groups:
  - name: critical
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected (>5%)"

      - alert: ServiceDown
        expr: up{job="youtopia-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "API service is down"

      - alert: OpenAIUnhealthy
        expr: health_check_openai == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "OpenAI API is unreachable"
```

#### 3.3.2 Warning Alerts (Slack notification)
```yaml
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency is above 5 seconds"

      - alert: HighLLMLatency
        expr: histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM responses are slow (>30s p95)"
```

---

## Environment Variables Summary

Add these to your deployment configurations:

### Backend (Render)
```env
# Sentry
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# Log Aggregation (Better Stack / Logtail)
LOGTAIL_SOURCE_TOKEN=xxx

# Tracing (Optional - Phase 2)
OTLP_ENDPOINT=https://otlp.example.com:4317

# Metrics (if using external Prometheus)
PROMETHEUS_PUSH_GATEWAY=https://prometheus.example.com
```

### Frontend (Vercel)
```env
# Sentry
VITE_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

### AWS Lambda (Slack Bot)
```env
# Sentry
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

---

## Implementation Checklist

### Phase 1 (Do before production launch)
- [ ] Create Sentry account and projects (frontend + backend)
- [ ] Add `sentry-sdk[fastapi]` to requirements.txt
- [ ] Create `src/utils/sentry.py` with initialization
- [ ] Integrate Sentry init into `server.py` startup
- [ ] Update exception handlers to add Sentry context
- [ ] Add `@sentry/react` to frontend
- [ ] Create `frontend/src/lib/sentry.ts`
- [ ] Initialize Sentry in `main.tsx`
- [ ] Add ErrorBoundary to App
- [ ] Create `src/middleware/request_context.py`
- [ ] Add RequestContextMiddleware to server
- [ ] Update frontend API client with request ID
- [ ] Create Better Stack account
- [ ] Add `logtail-python` to requirements.txt
- [ ] Update `src/utils/logging.py` with Logtail handler
- [ ] Create enhanced health check router
- [ ] Set up UptimeRobot monitors
- [ ] Add all environment variables to Render/Vercel

### Phase 2 (First month of production)
- [ ] Add Prometheus instrumentation
- [ ] Create custom metrics for LLM/RAG
- [ ] Instrument LLM client with metrics
- [ ] Instrument RAG retrieval with metrics
- [ ] Create `frontend/src/lib/logger.ts`
- [ ] Replace console.log in frontend with structured logging
- [ ] Set up Grafana Cloud account
- [ ] Create basic dashboards

### Phase 3 (As you scale)
- [ ] Add OpenTelemetry tracing
- [ ] Set up alerting rules
- [ ] Create SLO dashboards
- [ ] Implement log-based alerting
- [ ] Add custom business metrics

---

## Cost Estimates

| Service | Free Tier | Paid (if needed) |
|---------|-----------|------------------|
| Sentry | 5k errors/mo | $26/mo for 100k |
| Better Stack | 1GB logs/mo | $24/mo for 30GB |
| UptimeRobot | 50 monitors | $7/mo for 1-min checks |
| Grafana Cloud | Generous | ~$50/mo at scale |

**Phase 1 total: $0/month** (all free tiers)
**Phase 2-3 total: ~$50-100/month** (at moderate scale)

---

## Files to Create/Modify Summary

### New Files
- `src/utils/sentry.py` - Sentry configuration
- `src/utils/metrics.py` - Prometheus metrics definitions
- `src/utils/tracing.py` - OpenTelemetry setup
- `src/middleware/request_context.py` - Request ID middleware
- `src/api/routers/health.py` - Enhanced health checks
- `frontend/src/lib/sentry.ts` - Frontend Sentry config
- `frontend/src/lib/logger.ts` - Structured logging utility

### Modified Files
- `requirements.txt` - Add observability dependencies
- `frontend/package.json` - Add Sentry SDK
- `src/utils/logging.py` - Add Logtail integration
- `src/api/server.py` - Initialize Sentry, add middlewares
- `src/llm/client.py` - Add metrics instrumentation
- `src/rag/retriever.py` - Add metrics instrumentation
- `frontend/src/main.tsx` - Initialize Sentry
- `frontend/src/App.tsx` - Add ErrorBoundary
- `frontend/src/api/client.ts` - Add request ID, structured logging
