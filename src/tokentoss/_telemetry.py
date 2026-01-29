"""Telemetry stubs for future instrumentation.

All functions are no-ops. When a telemetry backend is added (e.g.
OpenTelemetry), these will be wired up without changing call sites.
"""


def trace_event(name: str, **attributes) -> None:
    """Record a trace event (no-op)."""


def increment_counter(name: str, value: int = 1, **tags) -> None:
    """Increment a metric counter (no-op)."""
