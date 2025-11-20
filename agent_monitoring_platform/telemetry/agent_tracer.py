from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from datetime import datetime
import uuid
import time
from .events import Event, EventType


@dataclass
class SpanAttribute:
    key: str
    value: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "PENDING"
    error: Optional[str] = None

    def add_attribute(self, key: str, value: Any):
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        event = {
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        }
        self.events.append(event)

    def end(self, status: str = "OK", error: Optional[str] = None):
        self.end_time = datetime.utcnow()
        self.status = status
        self.error = error

    def duration_ms(self) -> float:
        if not self.end_time:
            return -1
        return (self.end_time - self.start_time).total_seconds() * 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms(),
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
            "error": self.error,
        }


class AgentTracer:
    def __init__(self, metrics_registry=None, event_emitter=None):
        self.metrics_registry = metrics_registry
        self.event_emitter = event_emitter
        self.active_spans: Dict[str, Span] = {}
        self.completed_spans: List[Span] = []
        self.trace_stack: List[str] = []

    def start_trace(
        self, agent_id: str, trace_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None
    ) -> str:
        if not trace_id:
            trace_id = str(uuid.uuid4())

        span = Span(
            span_id=str(uuid.uuid4()),
            trace_id=trace_id,
            parent_span_id=None,
            operation_name=f"agent:{agent_id}",
            attributes={"agent_id": agent_id, **(context or {})},
        )

        self.active_spans[span.span_id] = span
        self.trace_stack.append(span.span_id)

        if self.event_emitter:
            self.event_emitter.emit_agent_event(agent_id, "AGENT_START", "Agent execution started", {"trace_id": trace_id})

        return trace_id

    def start_span(
        self, operation_name: str, trace_id: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None
    ) -> str:
        span_id = str(uuid.uuid4())
        parent_span_id = self.trace_stack[-1] if self.trace_stack else None

        if not trace_id and parent_span_id:
            trace_id = self.active_spans[parent_span_id].trace_id

        span = Span(
            span_id=span_id,
            trace_id=trace_id or str(uuid.uuid4()),
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            attributes=attributes or {},
        )

        self.active_spans[span_id] = span
        self.trace_stack.append(span_id)

        return span_id

    def end_span(self, span_id: str, status: str = "OK", error: Optional[str] = None):
        if span_id not in self.active_spans:
            return

        span = self.active_spans.pop(span_id)
        span.end(status, error)
        self.completed_spans.append(span)

        if self.trace_stack and self.trace_stack[-1] == span_id:
            self.trace_stack.pop()

        if self.metrics_registry and "span_duration" in self.metrics_registry.metrics:
            self.metrics_registry.get_metric("span_duration").record(span.duration_ms())

        if self.event_emitter:
            self.event_emitter.emit(Event(
                event_type="SPAN_ENDED",
                source=span.operation_name,
                data={"span_id": span_id, "status": status, "duration_ms": span.duration_ms()},
            ))

    def trace_agent_call(
        self, agent_id: str, input_data: Any, context: Optional[Dict[str, Any]] = None
    ) -> str:
        return self.start_trace(agent_id, context={"input": str(input_data)[:500], **(context or {})})

    def trace_tool_call(self, tool_name: str, tool_input: Any, attributes: Optional[Dict[str, Any]] = None) -> str:
        attrs = {
            "tool_name": tool_name,
            "input": str(tool_input)[:500],
            **(attributes or {}),
        }
        return self.start_span(f"tool:{tool_name}", attributes=attrs)

    def trace_llm_call(
        self, model: str, prompt_tokens: int, attributes: Optional[Dict[str, Any]] = None
    ) -> str:
        attrs = {
            "model": model,
            "prompt_tokens": prompt_tokens,
            **(attributes or {}),
        }
        return self.start_span(f"llm:{model}", attributes=attrs)

    def add_span_attribute(self, span_id: str, key: str, value: Any):
        if span_id in self.active_spans:
            self.active_spans[span_id].add_attribute(key, value)

    def add_span_event(self, span_id: str, event_name: str, attributes: Optional[Dict[str, Any]] = None):
        if span_id in self.active_spans:
            self.active_spans[span_id].add_event(event_name, attributes)

    def end_trace(self, trace_id: Optional[str] = None, status: str = "OK"):
        spans_to_end = list(self.active_spans.values())
        for span in spans_to_end:
            if not trace_id or span.trace_id == trace_id:
                self.end_span(span.span_id, status)

    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        return [span.to_dict() for span in self.completed_spans if span.trace_id == trace_id]

    def get_spans_by_operation(self, operation_name: str) -> List[Span]:
        return [span for span in self.completed_spans if span.operation_name == operation_name]

    def get_all_spans(self) -> List[Span]:
        return self.completed_spans

    def clear_spans(self):
        self.active_spans.clear()
        self.completed_spans.clear()
        self.trace_stack.clear()

    def get_statistics(self) -> Dict[str, Any]:
        stats = {
            "total_spans": len(self.completed_spans),
            "active_spans": len(self.active_spans),
            "by_operation": {},
        }

        for span in self.completed_spans:
            op = span.operation_name
            if op not in stats["by_operation"]:
                stats["by_operation"][op] = {"count": 0, "total_duration_ms": 0, "errors": 0}
            stats["by_operation"][op]["count"] += 1
            stats["by_operation"][op]["total_duration_ms"] += span.duration_ms()
            if span.status != "OK":
                stats["by_operation"][op]["errors"] += 1

        for op_stats in stats["by_operation"].values():
            if op_stats["count"] > 0:
                op_stats["avg_duration_ms"] = op_stats["total_duration_ms"] / op_stats["count"]

        return stats


from .events import Event
