import json
import sys
import os
from typing import Annotated, TypedDict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from dashboard.utils.aws_client import get_aws_client
from config.settings import AWS_REGION
@tool
def get_aws_cost_summary(days: int = 30) -> str:
    """Fetch AWS cost breakdown for the specified number of days."""
    try:
        client = get_aws_client(None)
        data = client.get_cost_breakdown(days=days)
        lines = [f"Total cost (last {days} days): ${data['total_cost']} {data['currency']}"]
        lines.append(f"Period: {data['start_date']} to {data['end_date']}")
        lines.append("\nBreakdown by service:")
        for svc in data["by_service"][:15]:  
            lines.append(f"  - {svc['service']}: ${svc['cost']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching costs: {str(e)}"
@tool
def get_ec2_instances(region: str = AWS_REGION) -> str:
    """List EC2 instances in the specified region."""
    try:
        client = get_aws_client(region)
        instances = client.list_ec2_instances()
        if not instances:
            return "No EC2 instances found."
        lines = [f"Found {len(instances)} EC2 instances:"]
        for inst in instances:
            lines.append(
                f"  [{inst['state'].upper()}] {inst['name']} ({inst['id']}) | "
                f"Type: {inst['type']} | Est. cost: ${inst['estimated_monthly_cost']}/mo"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing EC2: {str(e)}"
@tool
def get_rds_instances(region: str = AWS_REGION) -> str:
    """List RDS instances in the specified region."""
    try:
        client = get_aws_client(region)
        instances = client.list_rds_instances()
        if not instances:
            return "No RDS instances found."
        lines = [f"Found {len(instances)} RDS instances:"]
        for inst in instances:
            lines.append(
                f"  [{inst['state'].upper()}] {inst['name']} | "
                f"Engine: {inst['engine']} | Class: {inst['type']} | "
                f"Multi-AZ: {inst['multi_az']} | Storage: {inst['storage_gb']} GB"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing RDS: {str(e)}"
@tool
def get_s3_buckets() -> str:
    """List all S3 buckets."""
    try:
        client = get_aws_client(None)
        buckets = client.list_s3_buckets()
        if not buckets:
            return "No S3 buckets found."
        lines = [f"Found {len(buckets)} S3 buckets:"]
        for b in buckets:
            lines.append(
                f"  {b['name']} | Size: {b['size_gb']} GB | "
                f"Objects: {b['object_count']} | Est. cost: ${b['estimated_monthly_cost']}/mo"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing S3: {str(e)}"
@tool
def get_lambda_functions(region: str = AWS_REGION) -> str:
    """List Lambda functions in the specified region."""
    try:
        client = get_aws_client(region)
        functions = client.list_lambda_functions()
        if not functions:
            return "No Lambda functions found."
        lines = [f"Found {len(functions)} Lambda functions:"]
        for fn in functions:
            lines.append(
                f"  {fn['name']} | Runtime+Memory: {fn['type']} | "
                f"Timeout: {fn['timeout_sec']}s | Last modified: {fn['last_modified']}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing Lambda: {str(e)}"
@tool
def get_nat_gateways(region: str = AWS_REGION) -> str:
    """List NAT Gateways in the specified region."""
    try:
        client = get_aws_client(region)
        gateways = client.list_nat_gateways()
        if not gateways:
            return "No active NAT Gateways found."
        lines = [f"Found {len(gateways)} NAT Gateways (each costs ~$32+/month):"]
        for gw in gateways:
            lines.append(f"  [{gw['state'].upper()}] {gw['name']} ({gw['id']}) | VPC: {gw['vpc_id']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing NAT Gateways: {str(e)}"
SYSTEM_PROMPT = """You are CloudWise, an expert AWS Solutions Architect and FinOps specialist.
Your goal is to help users reduce their AWS costs through actionable, specific recommendations.
When analyzing costs:
1. Always FETCH live data using the available tools before making recommendations.
2. Identify the TOP cost drivers and provide specific, actionable advice for each.
3. Prioritize recommendations by potential savings (highest impact first).
4. Mention specific AWS features or services that can help (Reserved Instances, Savings Plans, S3 Intelligent-Tiering, etc.)
5. Be specific — mention actual resource IDs/names from the fetched data.
6. Quantify savings estimates where possible.
7. Group recommendations into: Quick Wins (immediate), Medium Term, and Long Term.
Always be concise, helpful, and educational. Explain WHY each recommendation saves money.
Format your final answer clearly with sections and bullet points."""
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
TOOLS = [
    get_aws_cost_summary,
    get_ec2_instances,
    get_rds_instances,
    get_s3_buckets,
    get_lambda_functions,
    get_nat_gateways,
]
class CostOptimizerAgent:
    def __init__(self, openai_api_key: str, model: str = "gpt-4o"):
        self.llm = ChatOpenAI(
            model=model,
            api_key=openai_api_key,
            temperature=0.3,
            streaming=False,
        )
        self.llm_with_tools = self.llm.bind_tools(TOOLS)
        self.graph = self._build_graph()
        self.app = self.graph.compile()
    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)
        def agent_node(state: AgentState):
            messages = state["messages"]
            response = self.llm_with_tools.invoke(messages)
            return {"messages": [response]}
        tool_node = ToolNode(TOOLS)
        def should_continue(state: AgentState):
            last_message = state["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tool_node)
        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        graph.add_edge("tools", "agent")
        return graph
    def ask(self, question: str, chat_history: list = None) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=question))
        result = self.app.invoke({"messages": messages})
        final_message = result["messages"][-1]
        output = final_message.content if hasattr(final_message, "content") else str(final_message)
        steps = []
        for msg in result["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    steps.append(f"Called tool: **{tc['name']}**")
        return {"output": output, "steps": steps}
    def ask_stream(self, question: str, chat_history: list = None):
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=question))
        for chunk in self.app.stream({"messages": messages}):
            if "agent" in chunk:
                agent_messages = chunk["agent"]["messages"]
                for msg in agent_messages:
                    if hasattr(msg, "content") and msg.content:
                        yield msg.content