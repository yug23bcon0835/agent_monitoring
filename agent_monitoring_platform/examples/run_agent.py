import os
import sys

# Add parent directory to path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_groq import ChatGroq
from langchain_classic.agents import load_tools
from langchain_classic.agents import AgentExecutor, create_react_agent
from telemetry.collector import TelemetryCollector
from langchain_core.prompts import PromptTemplate
from telemetry.exporters import JSONExporter
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

def main():
    # 1. Setup Your Platform
    print("🚀 Starting Monitoring Platform...")
    collector = TelemetryCollector()
    collector.add_exporter(JSONExporter("./real_agent_output"))
    collector.start()

    # 2. Create the Bridge
    # This connects the LangChain agent to your collector
    monitoring_callback = AgentMonitoringCallback(collector, agent_name="MathWizard_GPT4")

    # 3. Setup Real LangChain Agent
    # (Requires OPENAI_API_KEY environment variable)
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Please set GROQ_API_KEY environment variable to run this test.")
        collector.stop()
        return

    print("🤖 Initializing LangChain Agent...")
    llm = ChatGroq(temperature=0, model="llama-3.1-8b-instant")
    tools = load_tools(["llm-math"], llm=llm)

    prompt = PromptTemplate.from_template(REACT_PROMPT)

    agent = create_react_agent(llm, tools, prompt)
    
    agent = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True,
        handle_parsing_errors=True
    )

    # 4. Run the Agent with the Callback
    query = "What is 25 raised to the power of 0.43?"
    print(f"\n❓ Query: {query}\n")
    
    try:
        # Pass the callback here! This is the magic step.
        result = agent.invoke(
            {"input": query}, 
            config={"callbacks": [monitoring_callback]}
        )
        print(f"\n💡 Answer: {result['output']}")
    except Exception as e:
        print(f"Agent failed: {e}")
        import traceback
        traceback.print_exc()

    # 5. Cleanup and Export
    print("\n💾 Exporting Telemetry Data...")
    collector.stop() # Stops background threads
    collector.export_all() # Force final export
    
    # Verify metrics
    metric = collector.get_metric("agent_execution_duration")
    if metric and metric.values:
        print(f"✅ Success! Captured {len(metric.values)} execution record.")
    else:
        print("⚠️ Warning: No execution metrics captured.")

if __name__ == "__main__":
    main()