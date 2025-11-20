from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional, Any
from enum import Enum
from datetime import datetime
import uuid


class EventType(str, Enum):
    AGENT_START = "agent.start"
    AGENT_END = "agent.end"
    AGENT_ERROR = "agent.error"
    TOOL_START = "tool.start"
    TOOL_END = "tool.end"
    TOOL_ERROR = "tool.error"
    LLM_START = "llm.start"
    LLM_END = "llm.end"
    LLM_ERROR = "llm.error"
    METRIC_RECORDED = "metric.recorded"
    SYSTEM_HEALTH = "system.health"
    CUSTOM = "custom"


class EventSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Event:
    event_type: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)
    severity: EventSeverity = EventSeverity.INFO
    source: str = ""
    message: str = ""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        et_value = self.event_type.value if hasattr(self.event_type, "value") else str(self.event_type)
        return {
            "event_id": self.event_id,
            "event_type": et_value,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "source": self.source,
            "message": self.message,
            "data": self.data,
            "context": self.context,
        }


class EventHandler:
    def __init__(self, name: str):
        self.name = name

    def handle(self, event: Event):
        raise NotImplementedError


class LoggingEventHandler(EventHandler):
    def __init__(self, logger, name: str = "logging_handler"):
        super().__init__(name)
        self.logger = logger

    def handle(self, event: Event):
        et_value = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
        level = getattr(self.logger, event.severity.value, self.logger.info)
        level(f"[{et_value}] {event.message}", extra={"event": event.to_dict()})


class StorageEventHandler(EventHandler):
    def __init__(self, storage_backend, name: str = "storage_handler"):
        super().__init__(name)
        self.storage = storage_backend
        self.events: List[Event] = []

    def handle(self, event: Event):
        self.events.append(event)
        self.storage.store_event(event)

    def get_events(self, event_type: Optional[EventType] = None) -> List[Event]:
        if event_type:
            return [e for e in self.events if e.event_type == event_type]
        return self.events


class CallbackEventHandler(EventHandler):
    def __init__(self, callback: Callable[[Event], None], name: str = "callback_handler"):
        super().__init__(name)
        self.callback = callback

    def handle(self, event: Event):
        self.callback(event)


class FilteredEventHandler(EventHandler):
    def __init__(self, wrapped_handler: EventHandler, event_types: List[EventType], name: str = "filtered_handler"):
        super().__init__(name)
        self.wrapped_handler = wrapped_handler
        self.event_types = event_types

    def handle(self, event: Event):
        if event.event_type in self.event_types:
            self.wrapped_handler.handle(event)


class EventEmitter:
    def __init__(self):
        self.handlers: Dict[str, EventHandler] = {}
        self.event_history: List[Event] = []

    def subscribe(self, handler: EventHandler):
        self.handlers[handler.name] = handler

    def unsubscribe(self, handler_name: str):
        del self.handlers[handler_name]

    def emit(self, event: Event):
        self.event_history.append(event)
        for handler in self.handlers.values():
            try:
                handler.handle(event)
            except Exception as e:
                if isinstance(handler, LoggingEventHandler):
                    handler.logger.error(f"Error in event handler {handler.name}: {e}")

    def emit_agent_event(self, agent_id: str, event_type: EventType, message: str = "", data: Optional[Dict] = None):
        et_value = event_type.value if hasattr(event_type, "value") else str(event_type)
        event = Event(
            event_type=event_type,
            source=f"agent:{agent_id}",
            message=message,
            data=data or {},
            severity=EventSeverity.ERROR if "error" in et_value else EventSeverity.INFO,
        )
        self.emit(event)

    def emit_tool_event(self, tool_name: str, event_type: EventType, message: str = "", data: Optional[Dict] = None):
        et_value = event_type.value if hasattr(event_type, "value") else str(event_type)
        event = Event(
            event_type=event_type,
            source=f"tool:{tool_name}",
            message=message,
            data=data or {},
            severity=EventSeverity.ERROR if "error" in et_value else EventSeverity.INFO,
        )
        self.emit(event)

    def emit_llm_event(self, model: str, event_type: EventType, message: str = "", data: Optional[Dict] = None):
        et_value = event_type.value if hasattr(event_type, "value") else str(event_type)
        event = Event(
            event_type=event_type,
            source=f"llm:{model}",
            message=message,
            data=data or {},
            severity=EventSeverity.ERROR if "error" in et_value else EventSeverity.INFO,
        )
        self.emit(event)

    def get_events(self, event_type: Optional[EventType] = None) -> List[Event]:
        if event_type:
            return [e for e in self.event_history if e.event_type == event_type]
        return self.event_history

    def get_events_since(self, timestamp: datetime, event_type: Optional[EventType] = None) -> List[Event]:
        events = [e for e in self.event_history if e.timestamp >= timestamp]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events

    def clear_history(self):
        self.event_history.clear()

    def get_stats(self) -> Dict[str, Any]:
        by_type = {}
        by_severity = {}
        for event in self.event_history:
            et_value = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
            by_type[event.event_type.value] = by_type.get(et_value, 0) + 1
            by_severity[event.severity.value] = by_severity.get(event.severity.value, 0) + 1

        return {
            "total_events": len(self.event_history),
            "by_type": by_type,
            "by_severity": by_severity,
        }
