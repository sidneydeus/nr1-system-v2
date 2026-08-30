from __future__ import annotations

import os
from typing import Any, Dict, Optional

from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


_tracer: Optional[otel_trace.Tracer] = None
_otel_provider: Optional[TracerProvider] = None
_initialized: bool = False


def _to_otel_value(value: Any) -> Any:
    """Converte valor para tipo compatível com atributos OpenTelemetry.

    Atributos OTel devem ser: bool, int, float, str ou sequência deles.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (str, int, float)):
        return value
    if isinstance(value, dict):
        return {str(_to_otel_value(k)): _to_otel_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_otel_value(v) for v in value]
    return str(value)


def _ensure_otel_setup() -> None:
    global _tracer, _otel_provider, _initialized

    if _initialized:
        return

    _otel_provider = TracerProvider()
    otel_trace.set_tracer_provider(_otel_provider)

    # Console exporter for development/debugging
    console_exporter = ConsoleSpanExporter()
    _otel_provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # OTLP exporter to Jaeger/OTLP collector (if JAEGER_ENDPOINT is set)
    jaeger_endpoint = os.getenv("JAEGER_ENDPOINT")
    if jaeger_endpoint:
        from opentelemetry.exporter.otlp.proto.http import OTLPHttpExporter

        otlp_exporter = OTLPHttpExporter(endpoint=jaeger_endpoint.rstrip("/"))
        _otel_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    _tracer = otel_trace.get_tracer(__name__)
    _initialized = True


def is_otel_enabled() -> bool:
    """Verifica se OpenTelemetry está configurado."""
    return os.getenv("JAEGER_ENDPOINT", "") != ""


def trace_tool_invocation(
    tool_name: str,
    parameters: Dict[str, Any],
    result: Any,
    session_id: str,
    user_name: Optional[str] = None,
    sector: Optional[str] = None,
    classification: Optional[str] = None,
) -> None:
    """Registra invocação de ferramenta como span no OpenTelemetry/Jaeger."""
    _ensure_otel_setup()

    tracer = _tracer or otel_trace.get_tracer(__name__)
    attr_parameters = _to_otel_value(parameters)
    attr_result = _to_otel_value(result)

    with tracer.start_as_current_span(
        f"tool.{tool_name}",
        attributes={
            "session.id": session_id,
            "user.name": user_name or "",
            "sector": sector or "",
            "classification": classification or "",
            "tool": tool_name,
        },
    ) as span:
        span.set_attribute("tool.input", attr_parameters)
        span.set_attribute("tool.output", attr_result)


def trace_state_transition(
    from_status: str,
    to_status: str,
    session_id: str,
    user_name: Optional[str] = None,
    sector: Optional[str] = None,
    classification: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Registra transição de estado como span no OpenTelemetry/Jaeger."""
    _ensure_otel_setup()

    tracer = _tracer or otel_trace.get_tracer(__name__)
    attr_details = _to_otel_value(details) if details else None

    span_attrs: Dict[str, Any] = {
        "session.id": session_id,
        "user.name": user_name or "",
        "sector": sector or "",
        "classification": classification or "",
        "from": from_status,
        "to": to_status,
    }
    if attr_details is not None:
        span_attrs["state.details"] = attr_details

    with tracer.start_as_current_span(
        "state.transition",
        attributes=span_attrs,
    ) as span:
        span.set_attribute("state.from", from_status)
        span.set_attribute("state.to", to_status)


def trace_risk_classification(
    classification: str,
    session_id: str,
    user_name: Optional[str] = None,
    sector: Optional[str] = None,
    categories: Optional[list] = None,
    evidence: Optional[list] = None,
) -> None:
    """Registra classificação de risco como span no OpenTelemetry/Jaeger."""
    _ensure_otel_setup()

    tracer = _tracer or otel_trace.get_tracer(__name__)
    attr_categories = _to_otel_value(categories) if categories else None
    attr_evidence = _to_otel_value(evidence) if evidence else None

    span_attrs: Dict[str, Any] = {
        "session.id": session_id,
        "user.name": user_name or "",
        "sector": sector or "",
        "classification": classification,
        "categories_count": len(categories or []),
        "evidence_count": len(evidence or []),
    }
    if attr_categories is not None:
        span_attrs["risk.categories"] = attr_categories
    if attr_evidence is not None:
        span_attrs["risk.evidence_count"] = len(evidence) if evidence else 0

    # Set additional risk attributes with proper types
    if categories:
        span_attrs["risk.categories"] = _to_otel_value(categories)
    if evidence:
        span_attrs["risk.evidence"] = _to_otel_value(evidence)

    with tracer.start_as_current_span(
        "risk.classification",
        attributes=span_attrs,
    ) as span:
        span.set_attribute("risk.classification", classification)


def trace_webhook_event(
    event_type: str,
    payload: Dict[str, Any],
    session_id: str,
    success: bool,
    error: Optional[str] = None,
) -> None:
    """Registra evento de webhook como span no OpenTelemetry/Jaeger."""
    _ensure_otel_setup()

    tracer = _tracer or otel_trace.get_tracer(__name__)
    attr_payload = _to_otel_value(payload)
    attr_error = _to_otel_value(error) if error else None

    span_attrs: Dict[str, Any] = {
        "session.id": session_id,
        "event.type": event_type,
        "event.success": success,
    }
    if attr_error is not None:
        span_attrs["event.error"] = attr_error

    with tracer.start_as_current_span(
        f"webhook.{event_type}",
        attributes=span_attrs,
    ) as span:
        span.set_attribute("webhook.payload", attr_payload)
        span.set_attribute("webhook.output", {
            "success": success,
            "error": attr_error,
        })