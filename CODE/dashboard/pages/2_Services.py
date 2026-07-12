import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import streamlit as st
import pandas as pd
from dashboard.utils.aws_client import get_aws_client
from dashboard.utils.cost_utils import state_badge, format_cost

def get_resource_advice(resource_type: str, resource_data: str):
    from dashboard.utils.ai_agent import CostOptimizerAgent
    from config.settings import OPENAI_MODEL, OPENAI_API_KEY
    if "openai_api_key" not in st.session_state:
        st.session_state["openai_api_key"] = OPENAI_API_KEY
    api_key = st.session_state.get("openai_api_key")
    if not api_key or not api_key.startswith("sk-"):
        st.error("OpenAI API Key is missing or invalid. Please configure it in the AI Advisor page.")
        return
    with st.spinner(f"Analyzing {resource_type} for cost optimization..."):
        try:
            agent = CostOptimizerAgent(openai_api_key=api_key, model=OPENAI_MODEL)
            prompt = f"""Analyze this specific {resource_type} for cost optimization.
Rules:
1. Provide a maximum of 2 short bullet points of actionable advice or observations.
2. Consider the instance type, size, state, and typical use cases. If it's a large instance (like xlarge, 2xlarge or above), flag it as potentially expensive and suggest verifying if that much compute is actually needed or suggest right-sizing/Savings Plans.
3. If the resource is extremely small (like t2/t3.micro) AND running, or if it's already stopped, you can respond exactly with "No immediate optimization needed, costs are minimal."
Resource data: {resource_data}"""
            response = agent.ask(question=prompt)
            st.info(response["output"])
            if response.get("steps"):
                with st.expander("🔍 Agent reasoning"):
                    for step in response["steps"]:
                        st.markdown(f'<div style="font-size:0.8rem;color:gray;">{step}</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error fetching AI advice: {str(e)}")
st.set_page_config(page_title="AWS Services", layout="wide")
st.markdown("""
<style>
.section-header { font-size:1.3rem; font-weight:700; color:#FAFAFA;
  border-bottom:2px solid #FF9900; padding-bottom:6px; margin:16px 0 12px; }
.resource-card { background:#1E2530; border:1px solid #2E3A4E; border-radius:10px;
  padding:14px 18px; margin:6px 0; }
.resource-name { font-size:1rem; font-weight:700; color:#FAFAFA; }
.resource-meta { font-size:.82rem; color:#9AA3B2; margin-top:3px; }
.cost-pill { background:#252D3A; color:#FF9900; border-radius:20px;
  padding:2px 10px; font-size:.8rem; font-weight:600; display:inline-block; }
.stButton > button[kind="secondary"] { border-color:#FF6B6B; color:#FF6B6B; }
.stButton > button[kind="secondary"]:hover { background:#FF6B6B; color:white; }
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="section-header">AWS Service Manager</div>', unsafe_allow_html=True)
st.caption("View all running services and take management actions. Destructive actions require confirmation.")
region = st.session_state.get("aws_region", "us-east-1")
tabs = st.tabs(["EC2", "RDS", "S3", "Lambda", "ECS", "ElastiCache", "NAT Gateway"])

cache_key = f"cache_services_{region}"
if cache_key not in st.session_state or st.button("Refresh Services", key="refresh_services"):
    with st.spinner(f"Fetching all services in {region}..."):
        client = get_aws_client(region)
        st.session_state[cache_key] = client.get_all_services(region)

all_services = st.session_state.get(cache_key, {})

if all_services.get("errors"):
    with st.expander("Some services could not be fetched (expand to see details)"):
        for svc, err in all_services["errors"].items():
            st.warning(f"**{svc}**: {err}")

def show_action_result(result: dict, action: str, resource_id: str):
    is_success = False
    err_msg = "Unknown error"
    
    if result.get("success"):
        is_success =True
    elif "results" in result and isinstance(result["results"], list) and len(result["results"]) > 0:
        first_res = result["results"][0]
        if first_res.get("success"):
            is_success = True
        else:
            err_msg = first_res.get("error", first_res.get("message", "Unknown error"))
    else:
        err_msg = result.get("error", result.get("message", "Unknown error"))
        
    if is_success:
        st.success(f"{action} action sent for **{resource_id}**. AWS is processing the request.")
        if cache_key in st.session_state:
            del st.session_state[cache_key]
    else:
        st.error(f"Action failed: {err_msg}")

with tabs[0]:
    ec2_list = all_services.get("EC2", [])
    st.markdown(f"### EC2 Instances ({len(ec2_list)})")
    if not ec2_list:
        st.info("No EC2 instances found in this region.")
    else:
        for inst in ec2_list:
            with st.container():
                st.markdown(f"""
                <div class="resource-card">
                  <div class="resource-name">{inst['name']}</div>
                  <div class="resource-meta">
                    ID: <code>{inst['id']}</code> &nbsp;|&nbsp;
                    Type: <b>{inst['type']}</b> &nbsp;|&nbsp;
                    AZ: {inst['az']} &nbsp;|&nbsp;
                    IP: {inst['public_ip']} &nbsp;|&nbsp;
                    Launched: {inst['launch_time']}
                  </div>
                </div>
                """, unsafe_allow_html=True)
                col_state, col_cost, col_stop, col_start, col_term = st.columns([2, 2, 1.5, 1.5, 1.5])
                with col_state:
                    st.markdown(f"**Status:** {state_badge(inst['state'])}")
                with col_cost:
                    st.markdown(f"<span class='cost-pill'>~{format_cost(inst['estimated_monthly_cost'])}/mo</span>", unsafe_allow_html=True)
                
                inst_id = inst["id"]
                inst_state = inst["state"]
                
                with col_stop:
                    if inst_state == "running":
                        if st.button("Stop", key=f"stop_ec2_{inst_id}", help="Stop (not terminate) this instance"):
                            try:
                                client = get_aws_client(region)
                                result = client.stop_ec2_instance(inst_id)
                                show_action_result(result, "Stop", inst_id)
                            except Exception as e:
                                st.error(f"Error: {e}")
                
                with col_start:
                    if inst_state == "stopped":
                        if st.button("Start", key=f"start_ec2_{inst_id}", help="Start this stopped instance"):
                            try:
                                client = get_aws_client(region)
                                result = client.start_ec2_instance(inst_id)
                                show_action_result(result, "Start", inst_id)
                            except Exception as e:
                                st.error(f"Error: {e}")
                
                with col_term:
                    term_key = f"confirm_term_ec2_{inst_id}"
                    if inst_state not in ("terminated", "terminating"):
                        if st.button("Terminate", key=f"term_ec2_{inst_id}", type="secondary",
                                     help="PERMANENT — cannot be undone"):
                            st.session_state[term_key] = True
                        
                        if st.session_state.get(term_key):
                            st.warning(f"Are you SURE you want to **permanently terminate** `{inst_id}`? This CANNOT be undone.")
                            c_yes, c_no = st.columns(2)
                            with c_yes:
                                if st.button("Yes, Terminate", key=f"yes_term_{inst_id}"):
                                    try:
                                        client = get_aws_client(region)
                                        result = client.terminate_ec2_instance(inst_id)
                                        show_action_result(result, "Terminate", inst_id)
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                                    st.session_state[term_key] = False
                            with c_no:
                                if st.button("Cancel", key=f"no_term_{inst_id}"):
                                    st.session_state[term_key] = False
                
                with st.expander("AI Cost Optimization Advice"):
                    if st.button("Analyze with AI", key=f"btn_ai_ec2_{inst_id}", help="Get resource-specific cost optimization tips"):
                        get_resource_advice("EC2 instance", str(inst))
                
                st.markdown("---")

with tabs[1]:
    rds_list = all_services.get("RDS", [])
    st.markdown(f"### RDS Instances ({len(rds_list)})")
    if not rds_list:
        st.info("No RDS instances found in this region.")
    else:
        for db in rds_list:
            st.markdown(f"""
            <div class="resource-card">
              <div class="resource-name">{db['name']}</div>
              <div class="resource-meta">
                Engine: <b>{db['engine']}</b> &nbsp;|&nbsp;
                Class: <b>{db['type']}</b> &nbsp;|&nbsp;
                Storage: {db['storage_gb']} GB &nbsp;|&nbsp;
                Multi-AZ: {'Yes' if db['multi_az'] else 'No'}
              </div>
            </div>
            """, unsafe_allow_html=True)
            
            col_state, col1, col2 = st.columns([2, 1.5, 1.5])
            with col_state:
                st.markdown(f"**Status:** {state_badge(db['state'])}")
            
            db_id = db["id"]
            with col1:
                if db["state"] == "available":
                    if st.button("Stop DB", key=f"stop_rds_{db_id}", help="Stop this RDS instance"):
                        try:
                            client = get_aws_client(region)
                            result = client.stop_rds_instance(db_id)
                            show_action_result(result, "Stop", db_id)
                        except Exception as e:
                            st.error(f"Error: {e}")
            with col2:
                if db["state"] == "stopped":
                    if st.button("Start DB", key=f"start_rds_{db_id}"):
                        try:
                            client = get_aws_client(region)
                            result = client.start_rds_instance(db_id)
                            show_action_result(result, "Start", db_id)
                        except Exception as e:
                            st.error(f"Error: {e}")
                            
            with st.expander("AI Cost Optimization Advice"):
                if st.button("Analyze with AI", key=f"btn_ai_rds_{db_id}", help="Get resource-specific cost optimization tips"):
                    get_resource_advice("RDS instance", str(db))
                    
            st.markdown("---")

with tabs[2]:
    s3_list = all_services.get("S3", [])
    st.markdown(f"### S3 Buckets ({len(s3_list)})")
    if not s3_list:
        st.info("No S3 buckets found.")
    else:
        df_s3 = pd.DataFrame([{
            "Bucket Name": b["name"],
            "Region": b["region"],
            "Size (GB)": b["size_gb"],
            "Objects": b["object_count"],
            "Created": b["creation_date"],
            "Est. Cost/mo": f"${b['estimated_monthly_cost']}",
        } for b in s3_list])
        st.dataframe(df_s3, use_container_width=True, hide_index=True)
        
        st.markdown("**Get AI Advice for a bucket:**")
        adv_col1, adv_col2 = st.columns([3, 1])
        with adv_col1:
            bucket_to_advise = st.selectbox("Select bucket for advice", options=["— select —"] + [b["name"] for b in s3_list], key="s3_advise_select")
        with adv_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if bucket_to_advise != "— select —":
                if st.button("Get Advice", key="s3_advise_btn"):
                    bucket_data = next((b for b in s3_list if b["name"] == bucket_to_advise), None)
                    if bucket_data:
                        get_resource_advice("S3 bucket", str(bucket_data))
        
        st.markdown("**Delete a bucket** (will delete all contents first):")
        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            bucket_to_delete = st.selectbox("Select bucket to delete", options=["— select —"] + [b["name"] for b in s3_list], key="s3_delete_select")
        with del_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if bucket_to_delete != "— select —":
                if st.button("Delete Bucket", key="s3_delete_btn", type="secondary"):
                    st.session_state["confirm_s3_delete"] = True
                    
        if st.session_state.get("confirm_s3_delete") and bucket_to_delete != "— select —":
            st.error(f"**DANGER**: This will permanently delete bucket `{bucket_to_delete}` and ALL its contents!")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Yes, Delete Everything", key="confirm_s3_yes"):
                    with st.spinner("Deleting..."):
                        try:
                            client = get_aws_client(region)
                            result = client.empty_and_delete_s3_bucket(bucket_to_delete)
                            if result.get("success"):
                                st.success(f"Bucket `{bucket_to_delete}` deleted.")
                                if cache_key in st.session_state:
                                    del st.session_state[cache_key]
                            else:
                                st.error(f"Failed to delete bucket: {result.get('error', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {e}")
                    st.session_state["confirm_s3_delete"] = False
            with c2:
                if st.button("Cancel", key="cancel_s3_delete"):
                    st.session_state["confirm_s3_delete"] = False

with tabs[3]:
    lambda_list = all_services.get("Lambda", [])
    st.markdown(f"### Lambda Functions ({len(lambda_list)})")
    if not lambda_list:
        st.info("No Lambda functions found in this region.")
    else:
        df_lambda = pd.DataFrame([{
            "Function Name": fn["name"],
            "Runtime / Memory": fn["type"],
            "Timeout (s)": fn["timeout_sec"],
            "Code Size (MB)": fn["code_size_mb"],
            "Last Modified": fn["last_modified"],
        } for fn in lambda_list])
        st.dataframe(df_lambda, use_container_width=True, hide_index=True)
        
        st.markdown("**Get AI Advice for a Lambda function:**")
        adv_col1, adv_col2 = st.columns([3, 1])
        with adv_col1:
            lambda_to_advise = st.selectbox("Select function for advice", options=["— select —"] + [fn["name"] for fn in lambda_list], key="lambda_advise_select")
        with adv_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if lambda_to_advise != "— select —":
                if st.button("Get Advice", key="lambda_advise_btn"):
                    lambda_data = next((fn for fn in lambda_list if fn["name"] == lambda_to_advise), None)
                    if lambda_data:
                        get_resource_advice("Lambda function", str(lambda_data))

        st.markdown("**Delete a Lambda function:**")
        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            fn_to_delete = st.selectbox(
                "Select function to delete", options=["— select —"] + [fn["name"] for fn in lambda_list], key="lambda_delete_select")
        with del_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if fn_to_delete != "— select —":
                if st.button("Delete Function", key="lambda_delete_btn", type="secondary"):
                    st.session_state["confirm_lambda_delete"] = True
                    
        if st.session_state.get("confirm_lambda_delete") and fn_to_delete != "— select —":
            st.warning(f"Delete Lambda function `{fn_to_delete}`?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Yes, Delete", key="confirm_lambda_yes"):
                    try:
                        client = get_aws_client(region)
                        result = client.delete_lambda_function(fn_to_delete)
                        st.success(f"Function `{fn_to_delete}` deleted.")
                        if cache_key in st.session_state:
                            del st.session_state[cache_key]
                    except Exception as e:
                        st.error(f"Error: {e}")
                    st.session_state["confirm_lambda_delete"] = False
            with c2:
                if st.button("Cancel", key="cancel_lambda_delete"):
                    st.session_state["confirm_lambda_delete"] = False

with tabs[4]:
    ecs_list = all_services.get("ECS", [])
    st.markdown(f"### ECS Clusters ({len(ecs_list)})")
    if not ecs_list:
        st.info("No ECS clusters found in this region.")
    else:
        df_ecs = pd.DataFrame([{
            "Cluster Name": c["name"],
            "Status": state_badge(c["state"]),
            "Running Tasks": c["running_tasks"],
            "Pending Tasks": c["pending_tasks"],
            "Active Services": c["active_services"],
        } for c in ecs_list])
        st.dataframe(df_ecs, use_container_width=True, hide_index=True)
        
        st.markdown("**Get AI Advice for an ECS cluster:**")
        adv_col1, adv_col2 = st.columns([3, 1])
        with adv_col1:
            ecs_to_advise = st.selectbox("Select cluster for advice", options=["— select —"] + [c["name"] for c in ecs_list], key="ecs_advise_select")
        with adv_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if ecs_to_advise != "— select —":
                if st.button("Get Advice", key="ecs_advise_btn"):
                    ecs_data = next((c for c in ecs_list if c["name"] == ecs_to_advise), None)
                    if ecs_data:
                        get_resource_advice("ECS cluster", str(ecs_data))

with tabs[5]:
    ec_list = all_services.get("ElastiCache", [])
    st.markdown(f"### ElastiCache Clusters ({len(ec_list)})")
    if not ec_list:
        st.info("No ElastiCache clusters found in this region.")
    else:
        for ec in ec_list:
            col_info, col_state, col_del = st.columns([4, 2, 1.5])
            with col_info:
                st.markdown(f"**{ec['name']}** — {ec['engine']} | {ec['node_type']} | {ec['num_nodes']} node(s)")
            with col_state:
                st.markdown(state_badge(ec["state"]))
            with col_del:
                ec_id = ec["id"]
                if st.button("Delete", key=f"del_ec_{ec_id}", type="secondary"):
                    st.session_state[f"confirm_ec_{ec_id}"] = True
                
                if st.session_state.get(f"confirm_ec_{ec_id}"):
                    st.warning(f"Delete ElastiCache cluster `{ec_id}`?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Yes", key=f"yes_ec_{ec_id}"):
                            try:
                                client = get_aws_client(region)
                                client.delete_elasticache_cluster(ec_id)
                                st.success(f"Cluster `{ec_id}` deletion initiated.")
                            except Exception as e:
                                st.error(f"Error: {e}")
                            st.session_state[f"confirm_ec_{ec_id}"] = False
                    with c2:
                        if st.button("Cancel", key=f"no_ec_{ec_id}"):
                            st.session_state[f"confirm_ec_{ec_id}"] = False
                            
            with st.expander("AI Cost Optimization Advice"):
                if st.button("Analyze with AI", key=f"btn_ai_ec_{ec_id}", help="Get resource-specific cost optimization tips"):
                    get_resource_advice("ElastiCache cluster", str(ec))
            st.markdown("---")

with tabs[6]:
    nat_list = all_services.get("NAT Gateway", [])
    st.markdown(f"### NAT Gateways ({len(nat_list)})")
    st.caption("NAT Gateways cost ~$32+/month each regardless of traffic. Review carefully.")
    if not nat_list:
        st.info("No active NAT Gateways found in this region.")
    else:
        for gw in nat_list:
            col_info, col_state, col_cost, col_del = st.columns([3, 2, 2, 1.5])
            with col_info:
                st.markdown(f"**{gw['name']}** ({gw['id']})\n\nVPC: `{gw['vpc_id']}`")
            with col_state:
                st.markdown(state_badge(gw["state"]))
            with col_cost:
                st.markdown(f"<span style='color:#FF9900;font-weight:600'>~$32/mo min</span>", unsafe_allow_html=True)
            with col_del:
                gw_id = gw["id"]
                if st.button("Delete", key=f"del_nat_{gw_id}", type="secondary",
                             help="Delete this NAT Gateway. Ensure no subnets depend on it."):
                    st.session_state[f"confirm_nat_{gw_id}"] = True
                
                if st.session_state.get(f"confirm_nat_{gw_id}"):
                    st.warning(f"Delete NAT Gateway `{gw_id}`? Subnets routing through it will lose internet access.")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Yes, Delete", key=f"yes_nat_{gw_id}"):
                            try:
                                client = get_aws_client(region)
                                client.delete_nat_gateway(gw_id)
                                st.success(f"NAT Gateway `{gw_id}` deletion initiated.")
                            except Exception as e:
                                st.error(f"Error: {e}")
                            st.session_state[f"confirm_nat_{gw_id}"] = False
                    with c2:
                        if st.button("Cancel", key=f"no_nat_{gw_id}"):
                            st.session_state[f"confirm_nat_{gw_id}"] = False
                            
            with st.expander("AI Cost Optimization Advice"):
                if st.button("Analyze with AI", key=f"btn_ai_nat_{gw_id}", help="Get resource-specific cost optimization tips"):
                    get_resource_advice("NAT Gateway", str(gw))
            st.markdown("---")