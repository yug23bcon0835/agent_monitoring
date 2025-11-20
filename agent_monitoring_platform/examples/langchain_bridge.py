import time
from typing import Any, Dict, List, Optional
from uuid import UUID

# LangChain imports
from langchain_classic.callbacks.base import BaseCallbackHandler
from langchain_classic.schema import LLMResult

# Platform imports
from telemetry.collector import TelemetryCollector
from sessions import SessionManager


class AgentMonitoringCallback(BaseCallbackHandler):
    """Bridge LangChain callbacks into the Agent Monitoring Platform."""

    def __init__(
        self,
        collector: TelemetryCollector,
        agent_name: str,
        session_manager: Optional[SessionManager] = None,
        session_id: Optional[str] = None,
    ):
        self.collector = collector
        self.agent_name = agent_name
        self.session_manager = session_manager
        self.session_id = session_id
        self.runs: Dict[UUID, Dict[str, Any]] = {}
        self._llm_calls: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # LangChain lifecycle events
    # ------------------------------------------------------------------
    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        if parent_run_id is None:
            self.runs[run_id] = {"start_time": time.time(), "type": "agent", "inputs": inputs}

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_state = self.runs.get(run_id)
        if run_state and run_state.get("type") == "agent":
            duration_ms = (time.time() - run_state["start_time"]) * 1000
            self.collector.record_agent_execution(
                agent_id=self.agent_name,
                duration_ms=duration_ms,
                success=True,
                tokens_used=0,
                metadata={"outputs": str(outputs)[:200]},
            )
            self._record_session_run(
                inputs=run_state.get("inputs"),
                outputs=outputs,
                duration_ms=duration_ms,
                success=True,
            )
            print(f"✅ [Bridge] Recorded Agent Execution: {duration_ms:.2f}ms")
            self.runs.pop(run_id, None)

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_state = self.runs.get(run_id)
        if run_state and run_state.get("type") == "agent":
            duration_ms = (time.time() - run_state["start_time"]) * 1000
            self.collector.record_agent_execution(
                agent_id=self.agent_name,
                duration_ms=duration_ms,
                success=False,
                error=str(error),
            )
            self._record_session_run(
                inputs=run_state.get("inputs"),
                outputs={"error": str(error)},
                duration_ms=duration_ms,
                success=False,
                error=str(error),
            )
            print(f"❌ [Bridge] Recorded Agent Error: {error}")
            self.runs.pop(run_id, None)

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.runs[run_id] = {"start_time": time.time(), "type": "llm"}

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_state = self.runs.get(run_id)
        if not run_state:
            return

        latency_ms = (time.time() - run_state["start_time"]) * 1000
        token_usage = response.llm_output.get("token_usage", {}) if response.llm_output else {}
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        total_tokens = token_usage.get("total_tokens", 0)
        model_name = response.llm_output.get("model_name", "unknown-model") if response.llm_output else "unknown-model"

        self.collector.record_llm_call(
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            cost=total_tokens * 0.00002,
        )

        self._llm_calls.append(
            {
                "model": model_name,
                "latency_ms": latency_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "provider": "groq" if "grok" in model_name.lower() or "groq" in model_name.lower() else None,
            }
        )
        print(f"🤖 [Bridge] Recorded LLM Call: {latency_ms:.2f}ms ({total_tokens} tokens)")
        self.runs.pop(run_id, None)

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.runs[run_id] = {"start_time": time.time(), "type": "tool", "name": serialized.get("name", "unknown_tool")}

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_state = self.runs.get(run_id)
        if not run_state:
            return

        duration_ms = (time.time() - run_state["start_time"]) * 1000
        self.collector.record_tool_execution(
            tool_name=run_state.get("name", "unknown_tool"),
            duration_ms=duration_ms,
            success=True,
        )
        print(f"🛠️ [Bridge] Recorded Tool Usage: {run_state.get('name')} ({duration_ms:.2f}ms)")
        self.runs.pop(run_id, None)

    # ------------------------------------------------------------------
    # Session management helpers
    # ------------------------------------------------------------------
    def _record_session_run(
        self,
        *,
        inputs: Optional[Dict[str, Any]],
        outputs: Dict[str, Any],
        duration_ms: float,
        success: bool,
        error: Optional[str] = None,
    ):
        if not self.session_manager or not self.session_id:
            return

        events_snapshot = []
        if self.collector and self.collector.event_emitter:
            events_snapshot = [event.to_dict() for event in self.collector.event_emitter.get_events()][-50:]

        llm_summary = self._llm_calls[-1] if self._llm_calls else {}
        metrics = {"duration_ms": duration_ms}
        if llm_summary.get("total_tokens"):
            metrics["tokens_used"] = llm_summary["total_tokens"]
        if self._llm_calls:
            metrics["llm_calls"] = len(self._llm_calls)
            avg_latency = sum(call["latency_ms"] for call in self._llm_calls) / len(self._llm_calls)
            metrics["avg_llm_latency_ms"] = avg_latency

        lineage = {"llm": list(self._llm_calls)} if self._llm_calls else None

        self.session_manager.record_run(
            session_id=self.session_id,
            agent_id=self.agent_name,
            status="completed" if success else "failed",
            input_payload=inputs,
            output_payload=outputs,
            model=llm_summary.get("model"),
            provider=llm_summary.get("provider"),
            metrics=metrics,
            events=events_snapshot,
            error=error,
            tags={"bridge": "langchain", "source": "AgentMonitoringCallback"},
            lineage=lineage,
        )
        self._llm_calls.clear()
