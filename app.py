from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.marketing_campaign_roi_analysis import (
    add_metrics,
    build_budget_reallocation_plan,
    classify_campaign,
    classify_channel,
    decision_reason,
    main as run_pipeline,
)


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
CHART_DIR = OUTPUT_DIR / "charts"
HTML_REPORT = OUTPUT_DIR / "marketing_roi_report.html"

GROUPED_COLS = {
    "spend": "sum",
    "impressions": "sum",
    "clicks": "sum",
    "conversions": "sum",
    "new_customers": "sum",
    "revenue": "sum",
    "gross_profit": "sum",
}

MONEY_COLS = [
    "spend",
    "revenue",
    "gross_profit",
    "cpc",
    "cpa",
    "cac",
    "net_profit_after_marketing",
    "current_spend",
    "recommended_spend",
    "budget_change",
    "projected_revenue_change",
    "projected_profit_change",
]
PCT_COLS = ["ctr", "conversion_rate", "roi"]


st.set_page_config(page_title="Marketing Campaign ROI Analysis", layout="wide")


def ensure_outputs() -> None:
    required_files = [
        DATA_DIR / "marketing_campaign_data.csv",
        OUTPUT_DIR / "campaign_performance_summary.csv",
        OUTPUT_DIR / "channel_performance_summary.csv",
        OUTPUT_DIR / "budget_reallocation_plan.csv",
        HTML_REPORT,
    ]
    if not all(path.exists() for path in required_files):
        run_pipeline()


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    campaign_data = pd.read_csv(DATA_DIR / "marketing_campaign_data.csv", parse_dates=["date"])
    campaign_summary = pd.read_csv(OUTPUT_DIR / "campaign_performance_summary.csv")
    channel_summary = pd.read_csv(OUTPUT_DIR / "channel_performance_summary.csv")
    budget_plan = pd.read_csv(OUTPUT_DIR / "budget_reallocation_plan.csv")
    html_report = HTML_REPORT.read_text(encoding="utf-8")
    return campaign_data, campaign_summary, channel_summary, budget_plan, html_report


def summarize_filtered_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    campaign_summary = df.groupby(["campaign_id", "campaign_name", "channel", "funnel_stage"], as_index=False).agg(GROUPED_COLS)
    channel_summary = df.groupby("channel", as_index=False).agg(GROUPED_COLS)

    campaign_summary = add_metrics(campaign_summary)
    channel_summary = add_metrics(channel_summary)
    campaign_summary["net_profit_after_marketing"] = campaign_summary["gross_profit"] - campaign_summary["spend"]
    channel_summary["net_profit_after_marketing"] = channel_summary["gross_profit"] - channel_summary["spend"]
    campaign_summary["recommendation"] = campaign_summary.apply(classify_campaign, axis=1)
    campaign_summary["decision_reason"] = campaign_summary.apply(decision_reason, axis=1)
    channel_summary["budget_action"] = channel_summary.apply(classify_channel, axis=1)

    budget_plan = build_budget_reallocation_plan(campaign_summary)
    round_cols = [
        "spend",
        "conversions",
        "new_customers",
        "revenue",
        "gross_profit",
        "ctr",
        "conversion_rate",
        "cpc",
        "cpa",
        "cac",
        "roas",
        "roi",
        "net_profit_after_marketing",
    ]
    campaign_summary[round_cols] = campaign_summary[round_cols].round(3)
    channel_summary[round_cols] = channel_summary[round_cols].round(3)
    budget_plan[["current_spend", "recommended_spend", "budget_change", "projected_revenue_change", "projected_profit_change"]] = budget_plan[
        ["current_spend", "recommended_spend", "budget_change", "projected_revenue_change", "projected_profit_change"]
    ].round(2)
    return campaign_summary, channel_summary, budget_plan


def money(value: float) -> str:
    return f"${value:,.0f}"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def format_table(df: pd.DataFrame) -> pd.DataFrame:
    formatted = df.copy()
    for col in MONEY_COLS:
        if col in formatted:
            formatted[col] = formatted[col].map(lambda value: f"${value:,.0f}")
    for col in PCT_COLS:
        if col in formatted:
            formatted[col] = formatted[col].map(lambda value: f"{value * 100:.1f}%")
    if "roas" in formatted:
        formatted["roas"] = formatted["roas"].map(lambda value: f"{value:.2f}x")
    return formatted


ensure_outputs()
campaign_data_df, saved_campaign_summary_df, saved_channel_summary_df, saved_budget_plan_df, html_report = load_data()

st.sidebar.title("Pipeline Controls")
if st.sidebar.button("Refresh analysis outputs", width="stretch"):
    run_pipeline()
    st.cache_data.clear()
    st.rerun()

date_min = campaign_data_df["date"].min().date()
date_max = campaign_data_df["date"].max().date()
selected_dates = st.sidebar.date_input("Date range", value=(date_min, date_max), min_value=date_min, max_value=date_max)
if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date, end_date = date_min, date_max

channels = sorted(campaign_data_df["channel"].unique().tolist())
selected_channels = st.sidebar.multiselect("Channels", channels, default=channels)

campaigns = sorted(campaign_data_df["campaign_name"].unique().tolist())
selected_campaigns = st.sidebar.multiselect("Campaigns", campaigns, default=campaigns)

filtered_data = campaign_data_df[
    (campaign_data_df["date"].dt.date >= start_date)
    & (campaign_data_df["date"].dt.date <= end_date)
    & (campaign_data_df["channel"].isin(selected_channels))
    & (campaign_data_df["campaign_name"].isin(selected_campaigns))
]

if filtered_data.empty:
    st.warning("No rows match the current filters. Broaden the date, channel, or campaign selection.")
    st.stop()

campaign_summary_df, channel_summary_df, budget_plan_df = summarize_filtered_data(filtered_data)

total_spend = campaign_summary_df["spend"].sum()
total_revenue = campaign_summary_df["revenue"].sum()
total_gross_profit = campaign_summary_df["gross_profit"].sum()
total_profit = total_gross_profit - total_spend
new_customers = campaign_summary_df["new_customers"].sum()
blended_cac = total_spend / new_customers if new_customers else 0
overall_roi = total_profit / total_spend if total_spend else 0
projected_profit_change = budget_plan_df["projected_profit_change"].sum()

best_channel = channel_summary_df.sort_values("roi", ascending=False).iloc[0]
weakest_channel = channel_summary_df.sort_values("roi").iloc[0]

st.title("Marketing Campaign Performance + ROI Analysis")
st.caption("Live dashboard for CAC, ROAS, gross-profit ROI, campaign decisions, channel performance, and budget reallocation.")

kpi_1, kpi_2, kpi_3, kpi_4, kpi_5 = st.columns(5)
kpi_1.metric("Marketing Spend", money(total_spend))
kpi_2.metric("Revenue", money(total_revenue))
kpi_3.metric("Blended CAC", money(blended_cac))
kpi_4.metric("Gross-Profit ROI", pct(overall_roi))
kpi_5.metric("Projected Profit Lift", money(projected_profit_change))

st.info(
    f"Best channel: {best_channel['channel']} at {pct(best_channel['roi'])} ROI and {money(best_channel['cac'])} CAC. "
    f"Weakest channel: {weakest_channel['channel']} at {pct(weakest_channel['roi'])} ROI."
)

tab_overview, tab_channels, tab_campaigns, tab_budget, tab_report, tab_data = st.tabs(
    ["Overview", "Channels", "Campaigns", "Budget Plan", "Executive Report", "Data"]
)

with tab_overview:
    left, right = st.columns(2)
    with left:
        st.subheader("Spend vs Revenue")
        spend_revenue = channel_summary_df.set_index("channel")[["spend", "revenue"]].sort_values("revenue", ascending=False)
        st.bar_chart(spend_revenue)
    with right:
        st.subheader("ROI by Channel")
        roi_chart = channel_summary_df.set_index("channel")["roi"].sort_values(ascending=False)
        st.bar_chart(roi_chart)

    st.subheader("Decision Mix")
    decision_mix = campaign_summary_df["recommendation"].value_counts().rename_axis("recommendation").reset_index(name="campaign_count")
    st.dataframe(decision_mix, width="stretch", hide_index=True)

with tab_channels:
    st.subheader("Channel Performance")
    st.dataframe(format_table(channel_summary_df.sort_values("roi", ascending=False)), width="stretch", hide_index=True)
    left, right = st.columns(2)
    with left:
        st.image(str(CHART_DIR / "roi_by_channel.png"), caption="Full-period ROI by channel")
    with right:
        st.image(str(CHART_DIR / "spend_vs_revenue_by_channel.png"), caption="Full-period spend vs revenue")

with tab_campaigns:
    st.subheader("Campaign-Level Decisions")
    decision_options = ["All", "Scale", "Optimize", "Reduce / Test New Creative", "Stop"]
    decision = st.selectbox("Recommendation", decision_options)
    filtered_campaigns = campaign_summary_df if decision == "All" else campaign_summary_df[campaign_summary_df["recommendation"] == decision]
    st.dataframe(format_table(filtered_campaigns.sort_values("roi", ascending=False)), width="stretch", hide_index=True)
    st.image(str(CHART_DIR / "cac_by_campaign.png"), caption="Full-period CAC by campaign")

with tab_budget:
    st.subheader("Recommended Budget Reallocation Scenario")
    st.dataframe(format_table(budget_plan_df.sort_values("budget_change")), width="stretch", hide_index=True)
    st.image(str(CHART_DIR / "budget_reallocation.png"), caption="Full-period budget reallocation")

    col_a, col_b, col_c = st.columns(3)
    col_a.download_button("Download campaign summary", csv_bytes(campaign_summary_df), "campaign_performance_summary.csv", "text/csv", width="stretch")
    col_b.download_button("Download channel summary", csv_bytes(channel_summary_df), "channel_performance_summary.csv", "text/csv", width="stretch")
    col_c.download_button("Download budget plan", csv_bytes(budget_plan_df), "budget_reallocation_plan.csv", "text/csv", width="stretch")

with tab_report:
    st.subheader("Executive-Ready Report")
    st.download_button(
        "Download HTML report",
        html_report.encode("utf-8"),
        "marketing_roi_report.html",
        "text/html",
        width="stretch",
    )
    components.html(html_report, height=900, scrolling=True)

with tab_data:
    st.subheader("Filtered Source Data")
    st.dataframe(filtered_data.sort_values("date"), width="stretch", hide_index=True)
    st.download_button("Download filtered data", csv_bytes(filtered_data), "filtered_marketing_campaign_data.csv", "text/csv", width="stretch")

with st.sidebar.expander("Saved Pipeline Outputs", expanded=False):
    st.write(f"Campaign rows: {len(saved_campaign_summary_df):,}")
    st.write(f"Channel rows: {len(saved_channel_summary_df):,}")
    st.write(f"Budget rows: {len(saved_budget_plan_df):,}")
