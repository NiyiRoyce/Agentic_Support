"""OpenTelemetry tracing configuration."""

from typing import Any

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

try:
    from opentelemetry.instrumentation.fastapi import (
        FastAPIInstrumentor,
    )

    FASTAPI_INSTRUMENTOR_AVAILABLE = True
except ImportError:
    FASTAPI_INSTRUMENTOR_AVAILABLE = False

logger = logging.getLogger(__name__)


def configure_tracing(otlp_endpoint: str | None = None) -> None:
    """
    Configure OpenTelemetry tracing.

    Args:
        otlp_endpoint: OTLP gRPC endpoint URL
            (e.g., "http://localhost:4317")
    """
    # Create and register SDK tracer provider
    provider = TracerProvider()
    trace.set_tracer_provider(provider)

    if otlp_endpoint:
        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,  # Use TLS in production
        )

        span_processor = BatchSpanProcessor(otlp_exporter)

        # Add processor to SDK provider
        provider.add_span_processor(span_processor)

        logger.info(
            "OpenTelemetry tracing configured with OTLP endpoint: %s",
            otlp_endpoint,
        )
    else:
        logger.info("OpenTelemetry tracing configured (no exporter set)")


def instrument_fastapi(app: Any) -> None:
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
