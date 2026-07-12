import sys
import os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dashboard.utils.aws_client import get_aws_client
from dashboard.utils.cost_utils import format_cost
from config.settings import APP_TITLE, AWS_REGION
st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
/* Card styling */
.metric-card {
    background: linear-gradient(135deg, #1E2530 0%, #252D3A 100%);
    border: 1px solid #2E3A4E;
    border-radius: 12px;
    padding: 20px;
    margin: 8px 0;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.metric-title {
    color: #9AA3B2;
    font-size: 0.85rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
}
.metric-value {
    color: #FF9900;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
}
.metric-subtitle {
    color: #6B7A8D;
    font-size: 0.78rem;
    margin-top: 4px;
}
/* Status badges */
.badge-green  { color: #00C49F; font-weight: 600; }
.badge-red    { color: #FF6B6B; font-weight: 600; }
.badge-yellow { color: #FFC658; font-weight: 600; }
/* Sidebar */
.sidebar-info {
    background: #1A2030;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
    font-size: 0.82rem;
    color: #9AA3B2;
}
/* Section headers */
.section-header {
    font-size: 1.4rem;
    font-weight: 700;
    color: #FAFAFA;
    margin: 20px 0 12px;
    border-bottom: 2px solid #FF9900;
    padding-bottom: 6px;
}
/* Action button */
div[data-testid="stButton"] button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s;
}
</style>
""", unsafe_allow_html=True)
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/9/93/Amazon_Web_Services_Logo.svg", width=80)
    st.markdown(f"## {APP_TITLE}")
    st.markdown("---")
    st.markdown("### AWS Connection")
    if "aws_identity" not in st.session_state:
        with st.spinner("Connecting..."):
            client = get_aws_client(None)
            st.session_state.aws_identity = client.get_caller_identity()
    identity = st.session_state.aws_identity
    if identity.get("connected"):
        st.markdown(f'<span class="badge-green">Connected</span>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="sidebar-info">
        <b>Account ID:</b> {identity.get('account_id', '—')}<br>
        <b>ARN:</b> <span style="word-break:break-all;font-size:0.75rem">{identity.get('arn', '—')}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-red">Disconnected</span>', unsafe_allow_html=True)
        st.error(identity.get("error", "Unknown error"))
        st.info("Make sure `aws configure` has been run on this machine.")
    st.markdown("---")
    st.markdown("### AWS Region")
    region = st.selectbox(
        "Select region",
        options=[
            "us-east-1", "us-east-2", "us-west-1", "us-west-2",
            "eu-west-1", "eu-west-2", "eu-central-1",
            "ap-south-1", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1",
        ],
        index=0,
        key="aws_region",
        label_visibility="collapsed",
    )
    st.markdown("### Cost Period")
    
    today = datetime.today()
    default_start = today - timedelta(days=30)
    
    date_range = st.date_input(
        "Select Date Range",
        value=(default_start, today),
        max_value=today,
        help="Select a Start Date and End Date. (Note: The AWS API may be simulated to just use the number of days between the dates depending on backend implementation)."
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        period = (end_date - start_date).days
        if period < 1:
            period = 1 # Prevent 0 division
    else:
        period = 30 # Default if only one date selected
    
    st.markdown("---")
    if st.button("Refresh All Data", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("cache_"):
                del st.session_state[key]
        st.rerun()
    st.markdown("---")
    st.markdown('<div class="sidebar-info">Navigate using the <b>pages</b> in the sidebar above.</div>', unsafe_allow_html=True)
st.markdown(f'<div class="section-header">{APP_TITLE} — Dashboard Home</div>', unsafe_allow_html=True)
if not identity.get("connected"):
    st.warning("AWS credentials not configured. Please run `aws configure` in your terminal and restart the app.")
    st.stop()
col1, col2, col3, col4 = st.columns(4)
cache_key = f"cache_cost_{period}"
if cache_key not in st.session_state:
    with st.spinner("Fetching cost data..."):
        try:
            client = get_aws_client(None) 
            st.session_state[cache_key] = client.get_cost_breakdown(days=period)
        except Exception as e:
            st.session_state[cache_key] = None
            st.error(f"Could not fetch cost data: {e}")
cost_data = st.session_state.get(cache_key)
if cost_data:
    total = cost_data["total_cost"]
    services_count = len(cost_data["by_service"])
    top_service = cost_data["by_service"][0] if cost_data["by_service"] else {"service": "—", "cost": 0}
    with col1:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-title">Total Spend</div>
          <div class="metric-value">{format_cost(total)}</div>
          <div class="metric-subtitle">Last {period} days</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        daily_avg = round(total / period, 2) if period > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-title">Daily Average</div>
          <div class="metric-value">{format_cost(daily_avg)}</div>
          <div class="metric-subtitle">Per day cost</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-title">Top Service</div>
          <div class="metric-value" style="font-size:1.3rem">{top_service['service'].split(' ')[-1]}</div>
          <div class="metric-subtitle">{format_cost(top_service['cost'])} spent</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-title">Active Services</div>
          <div class="metric-value">{services_count}</div>
          <div class="metric-subtitle">With recorded spend</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("---")

    # Add Unified Graphs Section Below the Metrics
    st.markdown("### Cost Visualization")
    
    tab1, tab2 = st.tabs(["Cost by Service", "Cost Trend"])
    
    with tab1:
        chart_col1, chart_col2 = st.columns([3, 2])
        with chart_col1:
            df_service = pd.DataFrame(cost_data["by_service"][:15])
            if not df_service.empty:
                st.markdown("#### Top Services")
                fig_bar = px.bar(
                    df_service,
                    x="cost",
                    y="service",
                    orientation="h",
                    color="cost",
                    color_continuous_scale=["#1E3A5F", "#FF9900"],
                    labels={"cost": "Cost (USD)", "service": ""},
                    text=df_service["cost"].apply(lambda x: f"${x:.2f}"),
                )
                fig_bar.update_layout(
                    plot_bgcolor="#0E1117",
                    paper_bgcolor="#0E1117",
                    font_color="#FAFAFA",
                    height=350,
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=20, t=20, b=20),
                    yaxis={"categoryorder": "total ascending"},
                )
                fig_bar.update_traces(textposition="outside", textfont_color="#FF9900")
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No service data")
                
        with chart_col2:
            st.markdown("#### Cost Distribution")
            df_pie = pd.DataFrame(cost_data["by_service"][:10])
            if not df_pie.empty:
                colors = px.colors.qualitative.Pastel
                fig_pie = px.pie(
                    df_pie,
                    values="cost",
                    names="service",
                    color_discrete_sequence=colors,
                    hole=0.4,
                )
                fig_pie.update_layout(
                    plot_bgcolor="#0E1117",
                    paper_bgcolor="#0E1117",
                    font_color="#FAFAFA",
                    height=350,
                    margin=dict(l=10, r=10, t=20, b=20),
                    legend=dict(font=dict(size=10)),
                )
                fig_pie.update_traces(textinfo="percent", textfont_size=11)
                st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:
        st.markdown(f"#### Cost Trend (Last {period} days)")
        daily = cost_data.get("daily_trend", [])
        if daily:
            df_daily = pd.DataFrame(daily)
            df_daily["date"] = pd.to_datetime(df_daily["date"])
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=df_daily["date"],
                y=df_daily["cost"],
                mode="lines+markers",
                name="Cost",
                line=dict(color="#FF9900", width=2.5),
                marker=dict(size=5, color="#FF9900"),
                fill="tozeroy",
                fillcolor="rgba(255,153,0,0.08)",
                hovertemplate="<b>%{x|%b %d}</b><br>Cost: $%{y:.4f}<extra></extra>",
            ))
            
            # Show a 7-day moving average if period is large enough
            if period >= 7:
                df_daily["ma7"] = df_daily["cost"].rolling(7, min_periods=1).mean()
                fig_line.add_trace(go.Scatter(
                    x=df_daily["date"],
                    y=df_daily["ma7"],
                    mode="lines",
                    name="7-Day Avg",
                    line=dict(color="#00C49F", width=1.5, dash="dot"),
                ))
            
            fig_line.update_layout(
                plot_bgcolor="#0E1117",
                paper_bgcolor="#0E1117",
                font_color="#FAFAFA",
                height=350,
                margin=dict(l=10, r=10, t=10, b=40),
                xaxis=dict(gridcolor="#2E3A4E", tickformat="%b %d, %Y"),
                yaxis=dict(gridcolor="#2E3A4E", tickprefix="$"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode="x unified",
            )
            st.plotly_chart(fig_line, use_container_width=True)
            
            # Additional logic to determine viewing 'type' based on length (Daily vs Monthly/Yearly grouping context)
            if period > 60:
                st.info("Tip: For large date ranges, the graph above displays daily data points over the selected period. Use the chart tools to zoom in on specific months.")
        else:
            st.info(f"No daily trend data available for the last {period} days.")
            
else:
    st.info("No cost data available. This may mean you have a new AWS account or Cost Explorer is not yet enabled.")