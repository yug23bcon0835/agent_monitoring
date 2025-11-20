from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import SessionRecord, SessionRun


def _utcnow() -> datetime:
    return datetime.utcnow()


class SessionManager:
    """Lightweight session store for coordinating cross-session agent runs."""

    def __init__(self, storage_dir: str = "./real_agent_output/sessions", retention_days: int = 45):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.storage_file = self.storage_dir / "sessions.jsonl"
        self.retention_days = retention_days
        self._lock = Lock()
        self._sessions: Dict[str, SessionRecord] = {}
        self._load_sessions()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start_session(
        self,
        *,
        agent_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
        parent_session_id: Optional[str] = None,
    ) -> SessionRecord:
        session_id = str(uuid.uuid4())
        record = SessionRecord(
            session_id=session_id,
            agent_id=agent_id,
            name=name or f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            description=description,
            tags=tags or {},
            parent_session_id=parent_session_id,
        )
        with self._lock:
            self._sessions[session_id] = record
            self._persist_locked()
        return record

    def fork_session(
        self,
        parent_session_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> SessionRecord:
        parent = self._sessions.get(parent_session_id)
        if not parent:
            raise ValueError(f"Parent session {parent_session_id} not found")

        merged_tags = dict(parent.tags)
        if tags:
            merged_tags.update(tags)

        return self.start_session(
            agent_id=parent.agent_id,
            name=name or f"{parent.name} (follow-up)",
            description=description or parent.description,
            tags=merged_tags,
            parent_session_id=parent_session_id,
        )

    def close_session(self, session_id: str, status: str = "completed") -> Optional[SessionRecord]:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            session.complete(status)
            self._persist_locked()
            return session

    def record_run(
        self,
        session_id: str,
        *,
        agent_id: Optional[str] = None,
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
    ) -> SessionRun:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            run = SessionRun.build(
                run_id=str(uuid.uuid4()),
                session_id=session_id,
                agent_id=agent_id or session.agent_id,
                status=status,
                input_payload=input_payload,
                output_payload=output_payload,
                model=model,
                provider=provider,
                started_at=started_at or _utcnow(),
                completed_at=completed_at or _utcnow(),
                metrics=metrics,
                events=events,
                error=error,
                tags=tags,
                parent_run_id=parent_run_id,
                lineage=lineage,
            )
            if run.completed_at is None:
                run.completed_at = _utcnow()

            session.add_run(run)
            self._persist_locked()
            return run

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        return self._sessions.get(session_id)

    def list_sessions(self, agent_id: Optional[str] = None) -> List[SessionRecord]:
        sessions = [s for s in self._sessions.values() if not agent_id or s.agent_id == agent_id]
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    def get_recent_runs(
        self, *, agent_id: Optional[str] = None, limit: int = 20
    ) -> List[Tuple[SessionRecord, SessionRun]]:
        runs: List[Tuple[SessionRecord, SessionRun]] = []
        for session in self.list_sessions(agent_id=agent_id):
            for run in session.runs:
                runs.append((session, run))
        runs.sort(key=lambda payload: payload[1].completed_at or payload[1].started_at, reverse=True)
        return runs[:limit]

    def get_cross_session_summary(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        sessions = self.list_sessions(agent_id=agent_id)
        total_runs = sum(len(session.runs) for session in sessions)
        success_runs = sum(session.success_runs() for session in sessions)
        durations: List[float] = []
        last_run: Optional[datetime] = None

        for session in sessions:
            for run in session.runs:
                duration = run.duration_ms()
                if duration is None and run.metrics:
                    metric_duration = run.metrics.get("duration_ms")
                    if metric_duration is not None:
                        duration = float(metric_duration)
                if duration is not None:
                    durations.append(float(duration))
                finished_at = run.completed_at or run.started_at
                if finished_at and (not last_run or finished_at > last_run):
                    last_run = finished_at

        return {
            "total_sessions": len(sessions),
            "active_sessions": len([s for s in sessions if s.status == "active"]),
            "total_runs": total_runs,
            "success_rate": (success_runs / total_runs * 100.0) if total_runs else 0.0,
            "avg_duration_ms": (sum(durations) / len(durations)) if durations else 0.0,
            "last_run_at": last_run.isoformat() if last_run else None,
        }

    def cleanup(self):
        cutoff = _utcnow() - timedelta(days=self.retention_days)
        with self._lock:
            to_remove = [sid for sid, session in self._sessions.items() if session.updated_at < cutoff]
            for session_id in to_remove:
                del self._sessions[session_id]
            if to_remove:
                self._persist_locked()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load_sessions(self):
        if not self.storage_file.exists():
            return
        with self.storage_file.open("r") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                    session = SessionRecord.from_dict(payload)
                    self._sessions[session.session_id] = session
                except json.JSONDecodeError:
                    continue

    def _persist_locked(self):
        tmp_file = self.storage_file.with_suffix(".tmp")
        with tmp_file.open("w") as handle:
            for session in self._sessions.values():
                handle.write(json.dumps(session.to_dict()))
                handle.write("\n")
        tmp_file.replace(self.storage_file)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self._sessions)

    def __iter__(self) -> Iterable[SessionRecord]:
        return iter(self._sessions.values())
