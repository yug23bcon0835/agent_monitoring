from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.utcnow()


def _parse_datetime(value: Optional[Any]) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _trim_text(text: Optional[Any], limit: int = 500) -> Optional[str]:
    if text is None:
        return None
    text = str(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


@dataclass
class SessionRun:
    """Represents a single agent run that belongs to a monitoring session."""

    run_id: str
    session_id: str
    agent_id: str
    status: str
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    started_at: datetime = field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    parent_run_id: Optional[str] = None
    lineage: Dict[str, Any] = field(default_factory=dict)

    def duration_ms(self) -> Optional[float]:
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds() * 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "model": self.model,
            "provider": self.provider,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metrics": self.metrics,
            "events": self.events,
            "error": self.error,
            "tags": self.tags,
            "parent_run_id": self.parent_run_id,
            "lineage": self.lineage,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SessionRun":
        return cls(
            run_id=payload["run_id"],
            session_id=payload["session_id"],
            agent_id=payload.get("agent_id", "unknown"),
            status=payload.get("status", "completed"),
            input_summary=payload.get("input_summary"),
            output_summary=payload.get("output_summary"),
            model=payload.get("model"),
            provider=payload.get("provider"),
            started_at=_parse_datetime(payload.get("started_at")) or _utcnow(),
            completed_at=_parse_datetime(payload.get("completed_at")),
            metrics=payload.get("metrics") or {},
            events=payload.get("events") or [],
            error=payload.get("error"),
            tags=payload.get("tags") or {},
            parent_run_id=payload.get("parent_run_id"),
            lineage=payload.get("lineage") or {},
        )

    @classmethod
    def build(
        cls,
        *,
        run_id: str,
        session_id: str,
        agent_id: str,
        status: str = "completed",
        input_payload: Optional[Any] = None,
        output_payload: Optional[Any] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        metrics: Optional[Dict[str, Any]] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
        parent_run_id: Optional[str] = None,
        lineage: Optional[Dict[str, Any]] = None,
    ) -> "SessionRun":
        return cls(
            run_id=run_id,
            session_id=session_id,
            agent_id=agent_id,
            status=status,
            input_summary=_trim_text(input_payload),
            output_summary=_trim_text(output_payload, limit=1200),
            model=model,
            provider=provider,
            started_at=started_at or _utcnow(),
            completed_at=completed_at,
            metrics=metrics or {},
            events=events or [],
            error=error,
            tags=tags or {},
            parent_run_id=parent_run_id,
            lineage=lineage or {},
        )


@dataclass
class SessionRecord:
    """Envelope that groups multiple agent runs under a single monitoring session."""

    session_id: str
    agent_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    status: str = "active"
    tags: Dict[str, Any] = field(default_factory=dict)
    runs: List[SessionRun] = field(default_factory=list)
    parent_session_id: Optional[str] = None

    def add_run(self, run: SessionRun):
        self.runs.append(run)
        self.updated_at = _utcnow()

    def complete(self, status: str = "completed"):
        self.status = status
        self.updated_at = _utcnow()

    def success_runs(self) -> int:
        return len([run for run in self.runs if run.status == "completed" and not run.error])

    def total_duration_ms(self) -> float:
        durations = [run.duration_ms() for run in self.runs if run.duration_ms()]
        return sum(durations)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "tags": self.tags,
            "parent_session_id": self.parent_session_id,
            "runs": [run.to_dict() for run in self.runs],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SessionRecord":
        runs_payload = payload.get("runs") or []
        return cls(
            session_id=payload["session_id"],
            agent_id=payload.get("agent_id", "unknown"),
            name=payload.get("name", payload.get("session_id")),
            description=payload.get("description"),
            created_at=_parse_datetime(payload.get("created_at")) or _utcnow(),
            updated_at=_parse_datetime(payload.get("updated_at")) or _utcnow(),
            status=payload.get("status", "active"),
            tags=payload.get("tags") or {},
            runs=[SessionRun.from_dict(run_payload) for run_payload in runs_payload],
            parent_session_id=payload.get("parent_session_id"),
        )
