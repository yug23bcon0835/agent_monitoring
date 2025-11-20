import time
from typing import Dict, Any, List, Optional
from uuid import UUID

# LangChain imports
from langchain_classic.callbacks.base import BaseCallbackHandler
from langchain_classic.schema import LLMResult

# Your Platform imports
from telemetry.collector import TelemetryCollector

class AgentMonitoringCallback(BaseCallbackHandler):
    """
    A Bridge that connects LangChain events to the Agent Monitoring Platform.
    """
    def __init__(self, collector: TelemetryCollector, agent_name: str):
        self.collector = collector
        self.agent_name = agent_name
        self.runs = {}  # Store start times for calculating durations

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any) -> Any:
        # We only want to track the MAIN agent execution, not internal sub-chains
        if parent_run_id is None:
            self.runs[run_id] = {"start_time": time.time(), "type": "agent"}
            # Optional: Start a trace in your system
            # self.collector.agent_tracer.start_trace(self.agent_name)

    def on_chain_end(self, outputs: Dict[str, Any], *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any) -> Any:
        if run_id in self.runs and self.runs[run_id]["type"] == "agent":
            start_time = self.runs[run_id]["start_time"]
            duration_ms = (time.time() - start_time) * 1000
            
            # Record the full agent execution
            self.collector.record_agent_execution(
                agent_id=self.agent_name,
                duration_ms=duration_ms,
                success=True,
                # Estimate tokens if not provided (LangChain often puts them in llm_end)
                tokens_used=0, 
                metadata={"outputs": str(outputs)[:200]}
            )
            print(f"✅ [Bridge] Recorded Agent Execution: {duration_ms:.2f}ms")

    def on_chain_error(self, error: BaseException, *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any) -> Any:
        if run_id in self.runs and self.runs[run_id]["type"] == "agent":
            start_time = self.runs[run_id]["start_time"]
            duration_ms = (time.time() - start_time) * 1000
            
            self.collector.record_agent_execution(
                agent_id=self.agent_name,
                duration_ms=duration_ms,
                success=False,
                error=str(error)
            )
            print(f"❌ [Bridge] Recorded Agent Error: {error}")

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any) -> Any:
        self.runs[run_id] = {"start_time": time.time(), "type": "llm"}

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any) -> Any:
        if run_id in self.runs:
            start_time = self.runs[run_id]["start_time"]
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract token usage if available
            token_usage = response.llm_output.get("token_usage", {}) if response.llm_output else {}
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            completion_tokens = token_usage.get("completion_tokens", 0)
            total_tokens = token_usage.get("total_tokens", 0)
            
            # Record LLM Call
            self.collector.record_llm_call(
                model=response.llm_output.get("model_name", "unknown-model"),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                # Simple cost estimation logic (placeholder)
                cost=total_tokens * 0.00002 
            )
            print(f"🤖 [Bridge] Recorded LLM Call: {latency_ms:.2f}ms ({total_tokens} tokens)")

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any) -> Any:
        self.runs[run_id] = {
            "start_time": time.time(), 
            "type": "tool",
            "name": serialized.get("name", "unknown_tool")
        }

    def on_tool_end(self, output: str, *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any) -> Any:
        if run_id in self.runs:
            data = self.runs[run_id]
            duration_ms = (time.time() - data["start_time"]) * 1000
            
            # Record Tool Execution
            self.collector.record_tool_execution(
                tool_name=data["name"],
                duration_ms=duration_ms,
                success=True
            )
            print(f"🛠️ [Bridge] Recorded Tool Usage: {data['name']} ({duration_ms:.2f}ms)")