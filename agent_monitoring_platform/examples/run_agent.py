import os
import sys

# Add parent directory to path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_groq import ChatGroq
from langchain_classic.agents import load_tools
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

from telemetry.collector import TelemetryCollector
from telemetry.exporters import JSONExporter
from sessions import SessionManager
from examples.langchain_bridge import AgentMonitoringCallback

REACT_PROMPT = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""


def _resolve_session(session_manager: SessionManager, agent_id: str):
    resume_last = os.getenv("RESUME_LAST_SESSION", "false").lower() == "true"
    if resume_last:
        existing = session_manager.list_sessions(agent_id=agent_id)
        if existing:
            print("🔁 Resuming previous session for cross-run comparison...")
            parent = existing[0]
            return session_manager.fork_session(
                parent_session_id=parent.session_id,
                name=f"{parent.name} (cross-session)",
                tags={**parent.tags, "resumed": True},
            )

    return session_manager.start_session(
        agent_id=agent_id,
        name="Real Agent Runbook",
        description="Demo monitoring session for Groq-powered agent",
        tags={"source": "examples.run_agent"},
    )


def main():
    session_manager = SessionManager()
    agent_identifier = "MathWizard_GPT4"
    session = _resolve_session(session_manager, agent_identifier)

    # 1. Setup Telemetry and Exporters
    print("🚀 Starting Monitoring Platform...")
    collector = TelemetryCollector()
    collector.add_exporter(JSONExporter("./real_agent_output"))
    collector.start()

    # 2. Create the Bridge with session context
    monitoring_callback = AgentMonitoringCallback(
        collector,
        agent_name=agent_identifier,
        session_manager=session_manager,
        session_id=session.session_id,
    )

    # 3. Setup Real LangChain Agent (requires GROQ_API_KEY)
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Please set GROQ_API_KEY environment variable to run this test.")
        collector.stop()
        session_manager.close_session(session.session_id, status="failed")
        return

    print("🤖 Initializing LangChain Agent...")
    llm = ChatGroq(temperature=0, model="llama-3.1-8b-instant")
    tools = load_tools(["llm-math"], llm=llm)
    prompt = PromptTemplate.from_template(REACT_PROMPT)
    agent = create_react_agent(llm, tools, prompt)
    agent = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

    query = "What is 25 raised to the power of 0.43?"
    print(f"\n❓ Query: {query}\n")

    run_status = "completed"
    try:
        result = agent.invoke({"input": query}, config={"callbacks": [monitoring_callback]})
        print(f"\n💡 Answer: {result['output']}")
    except Exception as exc:
        run_status = "failed"
        print(f"Agent failed: {exc}")
        import traceback

        traceback.print_exc()
    finally:
        print("\n💾 Exporting Telemetry Data...")
        collector.stop()
        collector.export_all()
        session_manager.close_session(session.session_id, status=run_status)
        summary = session_manager.get_cross_session_summary(agent_id=agent_identifier)
        print(
            "📊 Cross-session summary -> sessions: {total_sessions}, runs: {total_runs}, success rate: {success_rate:.1f}%".format(
                **summary
            )
        )

        metric = collector.get_metric("agent_execution_duration")
        if metric and metric.values:
            print(f"✅ Success! Captured {len(metric.values)} execution record.")
        else:
            print("⚠️ Warning: No execution metrics captured.")


if __name__ == "__main__":
    main()
