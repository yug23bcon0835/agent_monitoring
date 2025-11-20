import os
import sys
import uuid

import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sessions import SessionManager
from telemetry.collector import TelemetryCollector
from examples.langchain_bridge import AgentMonitoringCallback


class _LLMResultStub:
    def __init__(self, llm_output):
        self.llm_output = llm_output


def test_session_manager_persists_runs(tmp_path):
    storage = tmp_path / "sessions"
    manager = SessionManager(storage_dir=str(storage))

    session = manager.start_session(agent_id="agent-1", name="Unit Test Session")
    manager.record_run(
        session_id=session.session_id,
        agent_id="agent-1",
        input_payload="hello",
        output_payload="world",
        metrics={"duration_ms": 123.4},
    )
    manager.close_session(session.session_id)

    reloaded = SessionManager(storage_dir=str(storage))
    loaded_session = reloaded.get_session(session.session_id)

    assert loaded_session is not None
    assert len(loaded_session.runs) == 1
    assert loaded_session.runs[0].metrics["duration_ms"] == pytest.approx(123.4)


def test_cross_session_summary(tmp_path):
    storage = tmp_path / "sessions"
    manager = SessionManager(storage_dir=str(storage))

    session_a = manager.start_session(agent_id="agent-2", name="Session A")
    session_b = manager.start_session(agent_id="agent-2", name="Session B")

    manager.record_run(session_id=session_a.session_id, status="completed", metrics={"duration_ms": 50})
    manager.record_run(
        session_id=session_b.session_id,
        status="failed",
        metrics={"duration_ms": 75},
        error="timeout",
    )

    summary = manager.get_cross_session_summary(agent_id="agent-2")
    assert summary["total_sessions"] == 2
    assert summary["total_runs"] == 2
    assert summary["success_rate"] == pytest.approx(50.0)
    assert summary["avg_duration_ms"] == pytest.approx(62.5)


def test_callback_records_session_runs(tmp_path):
    storage = tmp_path / "sessions"
    manager = SessionManager(storage_dir=str(storage))
    session = manager.start_session(agent_id="agent-cb", name="Callback Session")

    collector = TelemetryCollector()
    callback = AgentMonitoringCallback(
        collector,
        agent_name="agent-cb",
        session_manager=manager,
        session_id=session.session_id,
    )

    agent_run_id = uuid.uuid4()
    callback.on_chain_start({}, {"input": "2+2"}, run_id=agent_run_id, parent_run_id=None)

    llm_run_id = uuid.uuid4()
    callback.on_llm_start({}, ["prompt"], run_id=llm_run_id, parent_run_id=None)
    callback.on_llm_end(
        _LLMResultStub(
            {
                "model_name": "grok-beta",
                "token_usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
            }
        ),
        run_id=llm_run_id,
        parent_run_id=None,
    )

    callback.on_chain_end({"output": "4"}, run_id=agent_run_id, parent_run_id=None)
    manager.close_session(session.session_id)

    saved_session = manager.get_session(session.session_id)
    assert saved_session is not None
    assert len(saved_session.runs) == 1
    recorded_run = saved_session.runs[0]
    assert recorded_run.model == "grok-beta"
    assert recorded_run.metrics["llm_calls"] == 1
    assert recorded_run.metrics["tokens_used"] == 10
