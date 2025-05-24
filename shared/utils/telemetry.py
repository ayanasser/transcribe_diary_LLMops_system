#!/usr/bin/env python
# filepath: /home/aya/mlops_assessment/shared/utils/telemetry.py
from typing import Optional, Dict, Any
import socket

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from shared.config.settings import settings
from shared.utils.helpers import get_logger

logger = get_logger(__name__)

# Global tracer for reuse
_tracer = None

def setup_telemetry(service_name: str):
    """Initialize OpenTelemetry with OTLP exporter if configured"""
    global _tracer
    
    try:
        # Set up OpenTelemetry if observability is enabled and endpoint is configured
        if (hasattr(settings, "observability") and 
            settings.observability.enable_traces and 
            settings.observability.otlp_endpoint):
            
            resource = Resource.create({
                "service.name": service_name,
                "service.namespace": "mlops_assessment",
                "service.instance.id": socket.gethostname(),
                "deployment.environment": settings.environment
            })
            
            trace.set_tracer_provider(TracerProvider(resource=resource))
            
            # Set up exporter to send traces to collector (local or OTel collector)
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.observability.otlp_endpoint,
                insecure=settings.observability.otlp_insecure
            )
            
            span_processor = BatchSpanProcessor(otlp_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            _tracer = trace.get_tracer(service_name)
            
            logger.info(
                "OpenTelemetry initialized with OTLP exporter",
                service=service_name,
                endpoint=settings.observability.otlp_endpoint
            )
        else:
            # Initialize with no-op or basic tracer
            logger.info(
                "OpenTelemetry not configured, using basic tracer",
                service=service_name
            )
            trace.set_tracer_provider(TracerProvider())
            _tracer = trace.get_tracer(service_name)
            
    except Exception as e:
        logger.warning(
            "Failed to initialize OpenTelemetry, falling back to basic tracer",
            service=service_name,
            error=str(e)
        )
        # Fallback to basic tracer
        trace.set_tracer_provider(TracerProvider())
        _tracer = trace.get_tracer(service_name)
    
    return _tracer

def get_tracer() -> trace.Tracer:
    """Get the global tracer instance"""
    global _tracer
    if _tracer is None:
        # Create a default tracer if not set up yet
        _tracer = trace.get_tracer("default")
    return _tracer

def create_span(name: str, attributes: Optional[Dict[str, Any]] = None, parent: Optional[trace.SpanContext] = None):
    """Create a new span with the given name and attributes"""
    tracer = get_tracer()
    if parent:
        ctx = trace.set_span_in_context(parent)
        span = tracer.start_span(name, context=ctx)
    else:
        span = tracer.start_span(name)
    
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)
    
    return span

def extract_context_from_headers(headers: Dict[str, str]) -> trace.Context:
    """Extract trace context from HTTP headers"""
    return TraceContextTextMapPropagator().extract(headers)

def inject_context_into_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Inject current trace context into HTTP headers"""
    TraceContextTextMapPropagator().inject(headers)
    return headers
