import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from config.settings import OPENAI_API_KEY, OPENAI_MODEL
st.set_page_config(page_title="AI Cost Advisor", layout="wide")
st.markdown("""
<style>
.section-header { font-size:1.3rem; font-weight:700; color:#FAFAFA;
  border-bottom:2px solid #FF9900; padding-bottom:6px; margin:16px 0 12px; }
.chat-bubble-user { background:#1E3A5F; border-radius:12px 12px 2px 12px;
  padding:12px 16px; margin:8px 0; max-width:80%; margin-left:auto; }
.chat-bubble-ai { background:#1E2530; border:1px solid #2E3A4E;
  border-radius:12px 12px 12px 2px; padding:12px 16px; margin:8px 0; max-width:85%; }
.tool-step { background:#0D1E30; border-left:3px solid #FF9900;
  padding:6px 12px; border-radius:0 6px 6px 0; font-size:.82rem; color:#9AA3B2;
  margin:4px 0; }
.tip-btn { background:#1E2530; border:1px solid #FF9900; border-radius:20px;
  color:#FF9900; padding:4px 14px; font-size:.82rem; cursor:pointer; margin:4px; }
.agent-badge { background:linear-gradient(135deg,#FF9900,#FF6600);
  color:white; border-radius:6px; padding:2px 10px; font-size:.78rem;
  font-weight:700; display:inline-block; margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="section-header">AI Cost Optimization Advisor</div>', unsafe_allow_html=True)
if "openai_api_key" not in st.session_state:
    st.session_state["openai_api_key"] = OPENAI_API_KEY
openai_key = st.session_state.get("openai_api_key", "")
if not openai_key or not openai_key.startswith("sk-"):
    st.markdown("### Enter Your OpenAI API Key")
    st.info("Your key is stored only in this browser session and never saved to disk.")
    col_key, col_btn = st.columns([4, 1])
    with col_key:
        new_key = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="sk-...",
            key="openai_key_input",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("Set Key", use_container_width=True):
            if new_key.startswith("sk-"):
                st.session_state["openai_api_key"] = new_key
                st.success("API key saved for this session.")
                st.rerun()
            else:
                st.error("Invalid key format. Must start with `sk-`")
    st.stop()
if "ai_agent" not in st.session_state:
    with st.spinner("Initializing AI agent..."):
        try:
            from dashboard.utils.ai_agent import CostOptimizerAgent
            st.session_state["ai_agent"] = CostOptimizerAgent(
                openai_api_key=st.session_state["openai_api_key"],
                model=OPENAI_MODEL,
            )
        except Exception as e:
            st.error(f"Failed to initialize AI agent: {e}")
            st.stop()
agent = st.session_state["ai_agent"]
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "lc_history" not in st.session_state:
    st.session_state["lc_history"] = []
with st.sidebar:
    st.markdown("### AI Agent Info")
    st.markdown(f"""
    <div style="background:#1A2030;border-radius:8px;padding:12px;font-size:.82rem;color:#9AA3B2;">
    <b>Model:</b> {OPENAI_MODEL}<br>
    <b>Framework:</b> LangChain + LangGraph<br>
    <b>Tools:</b> 6 AWS data tools<br>
    <b>Persona:</b> CloudWise — AWS FinOps Expert
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### Agent Tools")
    tools_info = [
        ("get_aws_cost_summary", "Fetch cost by service"),
        ("get_ec2_instances", "List EC2 instances"),
        ("get_rds_instances", "List RDS databases"),
        ("get_s3_buckets", "List S3 buckets + sizes"),
        ("get_lambda_functions", "List Lambda functions"),
        ("get_nat_gateways", "List NAT Gateways"),
    ]
    for name, desc in tools_info:
        st.markdown(f"**`{name}`**  \n{desc}")
    st.markdown("---")
    if st.button("Clear Chat History", use_container_width=True):
        st.session_state["chat_history"] = []
        st.session_state["lc_history"] = []
        st.rerun()
    if st.button("Change API Key", use_container_width=True):
        st.session_state.pop("openai_api_key", None)
        st.session_state.pop("ai_agent", None)
        st.rerun()
st.markdown('<span class="agent-badge">CloudWise Agent Active</span>', unsafe_allow_html=True)
st.caption("Ask me anything about your AWS costs. I'll check your live AWS data and give specific advice.")
if not st.session_state["chat_history"]:
    st.markdown("#### Suggested Questions")
    suggestions = [
        "What are my top 5 cost drivers this month?",
        "Which EC2 instances can I stop or downsize to save money?",
        "Are there any idle or underutilised resources I should know about?",
        "Give me a full cost optimization plan with quick wins and long-term strategies.",
        "How much am I spending on NAT Gateways and how can I reduce it?",
        "What Reserved Instances or Savings Plans should I consider?",
    ]
    cols = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                st.session_state["pending_prompt"] = suggestion
                st.rerun()
for message in st.session_state["chat_history"]:
    role = message["role"]
    content = message["content"]
    steps = message.get("steps", [])
    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    else:
        with st.chat_message("assistant"):
            if steps:
                with st.expander(f"Agent reasoning ({len(steps)} tool calls)", expanded=False):
                    for step in steps:
                        st.markdown(f'<div class="tool-step">{step}</div>', unsafe_allow_html=True)
            st.markdown(content)
pending = st.session_state.pop("pending_prompt", None)
user_input = st.chat_input("Ask about your AWS costs...") or pending
if user_input:
    st.session_state["chat_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        with st.spinner("CloudWise is analyzing your AWS account..."):
            try:
                response = agent.ask(
                    question=user_input,
                    chat_history=st.session_state["lc_history"],
                )
                output = response["output"]
                steps = response["steps"]
                st.session_state["lc_history"].append(HumanMessage(content=user_input))
                st.session_state["lc_history"].append(AIMessage(content=output))
                if len(st.session_state["lc_history"]) > 20:
                    st.session_state["lc_history"] = st.session_state["lc_history"][-20:]
                if steps:
                    with st.expander(f"Agent reasoning ({len(steps)} tool calls)", expanded=True):
                        for step in steps:
                            st.markdown(f'<div class="tool-step">{step}</div>', unsafe_allow_html=True)
                st.markdown(output)
                st.session_state["chat_history"].append({
                    "role": "assistant",
                    "content": output,
                    "steps": steps,
                })
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                if "api_key" in str(e).lower() or "authentication" in str(e).lower():
                    error_msg = "OpenAI API key is invalid or expired. Click **Change API Key** in the sidebar."
                st.error(error_msg)
st.markdown("---")
st.caption("Powered by OpenAI GPT-4o • LangChain • LangGraph • AWS Cost Explorer API")