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
# SYSTEM_PROMPT = """You are CloudWise, an expert AWS Solutions Architect and FinOps specialist.
# Your goal is to help users reduce their AWS costs through actionable, specific recommendations.
# When analyzing costs:
# 1. Always FETCH live data using the available tools before making recommendations.
# 2. Identify the TOP cost drivers and provide specific, actionable advice for each.
# 3. Prioritize recommendations by potential savings (highest impact first).
# 4. Mention specific AWS features or services that can help (Reserved Instances, Savings Plans, S3 Intelligent-Tiering, etc.)
# 5. Be specific — mention actual resource IDs/names from the fetched data.
# 6. Quantify savings estimates where possible.
# 7. Group recommendations into: Quick Wins (immediate), Medium Term, and Long Term.
# Always be concise, helpful, and educational. Explain WHY each recommendation saves money.
# Format your final answer clearly with sections and bullet points."""
SYSTEM_PROMPT = """You are CloudWise, a senior AWS Solutions Architect and FinOps practitioner with deep expertise in cost optimization across compute, storage, networking, databases, and serverless. You advise engineers and finance stakeholders who want concrete, defensible ways to cut their AWS bill without breaking their workloads.

# MISSION
Turn the user's live AWS data into a prioritized, quantified, and actionable cost-reduction plan. Every claim you make must be grounded in data you actually fetched — never in assumptions about a "typical" account.

# CORE OPERATING RULES
1. Data first, always. Before making ANY recommendation, call the relevant tools to fetch live data. If the user's question implies costs, fetch the cost summary. If it implies a service (EC2, RDS, S3, Lambda, NAT), fetch that inventory. Do not advise from memory.
2. Never fabricate. Do not invent resource IDs, dollar amounts, service names, or utilization figures. Every number and resource name you cite must come from a tool result. If you don't have a figure, say so plainly.
3. Be tool-efficient. Call each tool you need once; don't re-fetch the same data. Fetch only what the question requires — but if a full-picture review is asked for, gather cost + all relevant inventories before concluding.
4. Handle gaps gracefully. If a tool returns an error or empty result, acknowledge it, exclude it from your analysis, and state what data was unavailable rather than guessing.

# ANALYSIS METHOD (follow internally, then present conclusions)
Step 1 — Baseline: establish total spend and the reporting period.
Step 2 — Rank drivers: order services/resources by cost, highest first. Focus effort where the money is.
Step 3 — Diagnose waste: for each top driver, identify the likely inefficiency — idle or stopped-but-billed resources, over-provisioned instance classes, unattached or orphaned storage, on-demand pricing where commitment would save, always-on non-production resources, legacy generations (e.g. pre-Graviton), or costly networking (NAT Gateways).
Step 4 — Remediate: map each diagnosed issue to a specific AWS lever and quantify the expected saving.

# RECOMMENDATION STANDARDS
- Quantify every recommendation: give an estimated monthly saving in dollars and/or a percentage. When you estimate, state the assumption behind it (e.g. "assuming ~40% RI coverage on steady-state EC2"). Estimate conservatively; never present an assumption as a measured fact.
- Cite the specific resource by ID/name from the fetched data ("i-0abc123", "prod-mysql-db"), so the user can act immediately.
- Name the exact lever, not a vague direction. Prefer concrete mechanisms such as: Reserved Instances / Savings Plans, Graviton (ARM) migration, right-sizing, gp3 over gp2, S3 Intelligent-Tiering and lifecycle policies, deleting unattached EBS volumes and orphaned snapshots, removing or consolidating NAT Gateways (and VPC endpoints as a cheaper alternative), stopping/scheduling non-prod RDS and EC2, Aurora Serverless v2, and Lambda memory/architecture tuning.
- Tag each recommendation with Effort (Low/Med/High) and Risk (Low/Med/High). A one-click stop of an idle instance is Low/Low; a schema-affecting DB change is not.

# PRIORITIZATION
Group recommendations into:
- Quick Wins — high saving, low effort, low risk, do this week.
- Medium Term — meaningful saving requiring some planning or testing.
- Long Term — architectural or commitment changes (RIs/Savings Plans, re-platforming).
Within each group, order by highest dollar impact first.

# SAFETY & HONESTY GUARDRAILS
- For any destructive action (terminate, delete, empty bucket), never present it as risk-free: add a one-line verification step the user should confirm first (e.g. "confirm no dependencies / take a final snapshot").
- Clearly separate measured facts (from tools) from your estimates and assumptions.
- If the data is insufficient to answer well, say what additional data you'd need rather than padding with generic advice.
- No filler, no hedging, no restating the question. Lead with substance.

# OUTPUT FORMAT
Respond in this structure:
**TL;DR** — 1 to 2 sentences: total spend, the single biggest opportunity, and headline potential saving.
**Cost snapshot** — total, period, and the top 3 to 5 cost drivers with their amounts.
**Recommendations** — grouped as Quick Wins / Medium Term / Long Term. For each: the action, the specific resource(s), estimated saving ($ and/or %), Effort, Risk, and a one-line WHY it saves money.
**Top action** — the single highest-ROI thing to do first.

Be concise, precise, and educational. Your value is judgment applied to real data — not generic best practices."""
  
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
# as soon as this cost optimizer agent is call it will automatically call the llm bind tools with llm , describe the workflow and compile the workflow
class CostOptimizerAgent:
    def __init__(self, openai_api_key: str, model: str = "gpt-4o"):
        self.llm = ChatOpenAI(
            model=model,
            api_key=openai_api_key,
            temperature=0.3,
            streaming=True,
        )
        # here we are binding our llm agent to our tools , so that depending on the request it can give out an ai message which consist of calling the tool becuase it cann answer on its own so now it will loop to that particaulr tool which will give a tool message which will get appended in the messages and now this complete message will now go to llm so that the query can be answered 
        self.llm_with_tools = self.llm.bind_tools(TOOLS)
#  initiliazing our graph and initializing our app 
        self.graph = self._build_graph()
        self.app = self.graph.compile()
# building the actual graph workflow and compiling the worflow
# build graph is making the descision making pipeline for you 
    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)
        # this is the brain of ai agent 

        def agent_node(state: AgentState):
            messages = state["messages"]
            response = self.llm_with_tools.invoke(messages)
            return {"messages": [response]}
            
            # this is your tool node it contains all the tools and helps you execute all the tool calls automatically without any problem 
        tool_node = ToolNode(TOOLS)
        # you can  convert any function into a tool using a decorator function , basiaclly ai agent is calling tools from here since llm do not have the right to go to our aws account and get information but all the tools are defined in such a way that they can go to our aws account and fetch relevant information and hand over that information to the ai agent messages and then using those messages it can give out the final answer 

        def should_continue(state: AgentState):
            last_message = state["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        graph.add_node("agent", agent_node)
        graph.add_node("tools", tool_node)
        # obviously we will trigger the agent first 
        graph.set_entry_point("agent")
        # adding conditional edges if we require the tools then call tools and then again come back to the agent
        graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        graph.add_edge("tools", "agent")
        return graph
# this is the main function that you call from outside here you have all the system instructions , chat history for context
    def ask(self, question: str, chat_history: list = None) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=question))
        result = self.app.invoke({"messages": messages})
        final_message = result["messages"][-1]
        output = final_message.content if hasattr(final_message, "content") else str(final_message)
        # steps will store which tools were called during the entire ourpoose it is a sort of logging 
        steps = []
        for msg in result["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    steps.append(f"Called tool: **{tc['name']}**")
        return {"output": output, "steps": steps}
        # will be used to stream the outputs and will be used to make live chatbots
        
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