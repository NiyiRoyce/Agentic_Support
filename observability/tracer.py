"""OpenTelemetry tracing configuration."""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FASTAPI_INSTRUMENTOR_AVAILABLE = True
except ImportError:
    FASTAPI_INSTRUMENTOR_AVAILABLE = False
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def configure_tracing(otlp_endpoint: Optional[str] = None) -> None:
    """
    Configure OpenTelemetry tracing.

    Args:
        otlp_endpoint: OTLP gRPC endpoint URL (e.g., "http://localhost:4317")
    """
    # Set up tracer provider
    trace.set_tracer_provider(TracerProvider())

    if otlp_endpoint:
        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,  # For local development; use TLS in production
        )
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        logger.info(
            f"OpenTelemetry tracing configured with OTLP endpoint: {otlp_endpoint}"
        )
    else:
        logger.info("OpenTelemetry tracing configured (no exporter set)")


def instrument_fastapi(app) -> None:
    """
    Instrument FastAPI application with OpenTelemetry.

    Args:
        app: FastAPI application instance
    """
    if FASTAPI_INSTRUMENTOR_AVAILABLE:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented with OpenTelemetry")
    else:
        logger.warning("OpenTelemetry FastAPI instrumentation not available")


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer instance.

    Args:
        name: Tracer name

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)
