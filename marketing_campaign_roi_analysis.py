from __future__ import annotations

import base64
from dataclasses import dataclass
from html import escape
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
CHART_DIR = OUTPUT_DIR / "charts"


@dataclass(frozen=True)
class CampaignConfig:
    campaign_id: str
    campaign_name: str
    channel: str
    funnel_stage: str
    daily_budget: float
    cpm: float
    ctr: float
    conversion_rate: float
    new_customer_rate: float
    avg_order_value: float
    gross_margin: float


CAMPAIGNS = [
    CampaignConfig("C001", "Google Search - High Intent", "Google Search", "Conversion", 1400, 28, 0.047, 0.092, 0.88, 96, 0.58),
    CampaignConfig("C002", "Google Shopping - Best Sellers", "Google Shopping", "Conversion", 1150, 24, 0.036, 0.068, 0.82, 88, 0.55),
    CampaignConfig("C003", "Facebook Retargeting", "Facebook", "Retargeting", 820, 18, 0.030, 0.055, 0.62, 82, 0.56),
    CampaignConfig("C004", "Facebook Prospecting - Broad", "Facebook", "Awareness", 1250, 14, 0.019, 0.026, 0.91, 76, 0.53),
    CampaignConfig("C005", "Instagram Creator Ads", "Instagram", "Consideration", 900, 16, 0.017, 0.020, 0.87, 72, 0.52),
    CampaignConfig("C006", "TikTok Video Views", "TikTok", "Awareness", 760, 10, 0.024, 0.012, 0.94, 66, 0.50),
    CampaignConfig("C007", "Email Winback", "Email", "Retention", 180, 4, 0.088, 0.120, 0.18, 74, 0.61),
    CampaignConfig("C008", "Affiliate Partner Deals", "Affiliate", "Conversion", 520, 12, 0.041, 0.082, 0.76, 84, 0.54),
    CampaignConfig("C009", "LinkedIn B2B Trial Push", "LinkedIn", "Experiment", 980, 42, 0.011, 0.018, 0.96, 112, 0.57),
    CampaignConfig("C010", "Instagram Story Sale", "Instagram", "Promotion", 640, 15, 0.021, 0.031, 0.79, 68, 0.50),
]


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)


def generate_campaign_data(seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-01-01", periods=180, freq="D")
    rows = []

    for config in CAMPAIGNS:
        for date in dates:
            weekday_factor = 1.08 if date.dayofweek in [1, 2, 3] else 0.94 if date.dayofweek in [5, 6] else 1.0
            month_factor = 1.12 if date.month in [3, 5] else 0.92 if date.month == 1 else 1.0
            promo_factor = 1.18 if date.day in [1, 15, 28] and config.funnel_stage in ["Promotion", "Retargeting"] else 1.0

            spend = config.daily_budget * rng.uniform(0.82, 1.18) * weekday_factor
            impressions = spend / config.cpm * 1000 * rng.lognormal(0, 0.06)
            clicks = impressions * config.ctr * rng.lognormal(0, 0.09)
            conversions = clicks * config.conversion_rate * month_factor * promo_factor * rng.lognormal(0, 0.10)
            new_customers = conversions * config.new_customer_rate * rng.lognormal(0, 0.05)
            revenue = conversions * config.avg_order_value * rng.lognormal(0, 0.07)
            gross_profit = revenue * config.gross_margin

            rows.append(
                {
                    "date": date,
                    "campaign_id": config.campaign_id,
                    "campaign_name": config.campaign_name,
                    "channel": config.channel,
                    "funnel_stage": config.funnel_stage,
                    "spend": round(spend, 2),
                    "impressions": int(round(impressions)),
                    "clicks": int(round(clicks)),
                    "conversions": round(conversions, 1),
                    "new_customers": round(new_customers, 1),
                    "revenue": round(revenue, 2),
                    "gross_profit": round(gross_profit, 2),
                }
            )

    campaign_data = pd.DataFrame(rows)
    campaign_data.to_csv(DATA_DIR / "marketing_campaign_data.csv", index=False)
    return campaign_data


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["ctr"] = result["clicks"] / result["impressions"]
    result["conversion_rate"] = result["conversions"] / result["clicks"]
    result["cpc"] = result["spend"] / result["clicks"]
    result["cpa"] = result["spend"] / result["conversions"]
    result["cac"] = result["spend"] / result["new_customers"]
    result["roas"] = result["revenue"] / result["spend"]
    result["roi"] = (result["gross_profit"] - result["spend"]) / result["spend"]
    return result.replace([np.inf, -np.inf], np.nan).fillna(0)


def summarize_performance(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    grouped_cols = {
        "spend": "sum",
        "impressions": "sum",
        "clicks": "sum",
        "conversions": "sum",
        "new_customers": "sum",
        "revenue": "sum",
        "gross_profit": "sum",
    }

    campaign_summary = df.groupby(["campaign_id", "campaign_name", "channel", "funnel_stage"], as_index=False).agg(grouped_cols)
    channel_summary = df.groupby("channel", as_index=False).agg(grouped_cols)

    campaign_summary = add_metrics(campaign_summary)
    channel_summary = add_metrics(channel_summary)

    campaign_summary["net_profit_after_marketing"] = campaign_summary["gross_profit"] - campaign_summary["spend"]
    channel_summary["net_profit_after_marketing"] = channel_summary["gross_profit"] - channel_summary["spend"]

    campaign_summary["recommendation"] = campaign_summary.apply(classify_campaign, axis=1)
    campaign_summary["decision_reason"] = campaign_summary.apply(decision_reason, axis=1)

    channel_summary["budget_action"] = channel_summary.apply(classify_channel, axis=1)

    budget_plan = build_budget_reallocation_plan(campaign_summary)

    round_cols = ["spend", "conversions", "new_customers", "revenue", "gross_profit", "ctr", "conversion_rate", "cpc", "cpa", "cac", "roas", "roi", "net_profit_after_marketing"]
    campaign_summary[round_cols] = campaign_summary[round_cols].round(3)
    channel_summary[round_cols] = channel_summary[round_cols].round(3)
    budget_plan[["current_spend", "recommended_spend", "budget_change", "projected_revenue_change", "projected_profit_change"]] = budget_plan[
        ["current_spend", "recommended_spend", "budget_change", "projected_revenue_change", "projected_profit_change"]
    ].round(2)

    campaign_summary.to_csv(OUTPUT_DIR / "campaign_performance_summary.csv", index=False)
    channel_summary.to_csv(OUTPUT_DIR / "channel_performance_summary.csv", index=False)
    budget_plan.to_csv(OUTPUT_DIR / "budget_reallocation_plan.csv", index=False)
    return campaign_summary, channel_summary, budget_plan


def classify_campaign(row: pd.Series) -> str:
    if row["roi"] >= 0.45 and row["cac"] <= 45:
        return "Scale"
    if row["roi"] < 0 or row["cac"] >= 95:
        return "Stop"
    if row["roas"] >= 1.8 and row["conversion_rate"] >= 0.035:
        return "Optimize"
    return "Reduce / Test New Creative"


def decision_reason(row: pd.Series) -> str:
    if row["recommendation"] == "Scale":
        return "Strong ROI and efficient customer acquisition."
    if row["recommendation"] == "Stop":
        return "Negative ROI or CAC is too high to justify continued spend."
    if row["recommendation"] == "Optimize":
        return "Revenue is promising, but CAC or ROI can improve with targeting and landing-page tests."
    return "Weak efficiency; lower budget until creative, audience, or offer improves."


def classify_channel(row: pd.Series) -> str:
    if row["roi"] >= 0.35 and row["cac"] <= 55:
        return "Invest More"
    if row["roi"] < 0:
        return "Cut Budget"
    return "Hold and Optimize"


def build_budget_reallocation_plan(campaign_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in campaign_summary.iterrows():
        if row["recommendation"] == "Scale":
            multiplier = 1.25
        elif row["recommendation"] == "Optimize":
            multiplier = 1.05
        elif row["recommendation"] == "Stop":
            multiplier = 0.15
        else:
            multiplier = 0.65

        current_spend = row["spend"]
        recommended_spend = current_spend * multiplier
        budget_change = recommended_spend - current_spend
        marginal_efficiency = max(row["roas"] * 0.82, 0)
        projected_revenue_change = budget_change * marginal_efficiency
        projected_profit_change = projected_revenue_change * (row["gross_profit"] / row["revenue"]) - budget_change if row["revenue"] else -budget_change

        rows.append(
            {
                "campaign_name": row["campaign_name"],
                "channel": row["channel"],
                "recommendation": row["recommendation"],
                "current_spend": current_spend,
                "recommended_spend": recommended_spend,
                "budget_change": budget_change,
                "projected_revenue_change": projected_revenue_change,
                "projected_profit_change": projected_profit_change,
            }
        )

    return pd.DataFrame(rows)


def build_charts(campaign_summary: pd.DataFrame, channel_summary: pd.DataFrame, budget_plan: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")

    channel_sorted = channel_summary.sort_values("roi", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#2f7d5c" if value >= 0.35 else "#d08b36" if value >= 0 else "#b94f45" for value in channel_sorted["roi"]]
    ax.barh(channel_sorted["channel"], channel_sorted["roi"], color=colors)
    ax.axvline(0, color="#333333", linewidth=1)
    ax.set_title("Marketing ROI by Channel", fontsize=14, fontweight="bold")
    ax.set_xlabel("ROI based on gross profit")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "roi_by_channel.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(channel_summary))
    width = 0.36
    ax.bar(x - width / 2, channel_summary["spend"], width, label="Spend", color="#6b7280")
    ax.bar(x + width / 2, channel_summary["revenue"], width, label="Revenue", color="#2f6f73")
    ax.set_xticks(x)
    ax.set_xticklabels(channel_summary["channel"], rotation=20, ha="right")
    ax.set_title("Spend vs Revenue by Channel", fontsize=14, fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(CHART_DIR / "spend_vs_revenue_by_channel.png", dpi=180)
    plt.close(fig)

    campaign_sorted = campaign_summary.sort_values("cac", ascending=False)
    fig, ax = plt.subplots(figsize=(11, 6))
    colors = ["#b94f45" if rec == "Stop" else "#d08b36" if "Reduce" in rec else "#2f7d5c" if rec == "Scale" else "#4f79a7" for rec in campaign_sorted["recommendation"]]
    ax.barh(campaign_sorted["campaign_name"], campaign_sorted["cac"], color=colors)
    ax.set_title("Customer Acquisition Cost by Campaign", fontsize=14, fontweight="bold")
    ax.set_xlabel("CAC")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "cac_by_campaign.png", dpi=180)
    plt.close(fig)

    plan_sorted = budget_plan.sort_values("budget_change")
    fig, ax = plt.subplots(figsize=(11, 6))
    colors = ["#b94f45" if value < 0 else "#2f7d5c" for value in plan_sorted["budget_change"]]
    ax.barh(plan_sorted["campaign_name"], plan_sorted["budget_change"], color=colors)
    ax.axvline(0, color="#333333", linewidth=1)
    ax.set_title("Recommended Budget Reallocation", fontsize=14, fontweight="bold")
    ax.set_xlabel("Budget change")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "budget_reallocation.png", dpi=180)
    plt.close(fig)


def money(value: float) -> str:
    return f"${value:,.0f}"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    text_df = df.copy().astype(str)
    headers = list(text_df.columns)
    rows = text_df.values.tolist()
    widths = [
        max(len(header), *(len(row[col_idx]) for row in rows)) if rows else len(header)
        for col_idx, header in enumerate(headers)
    ]
    header_line = "| " + " | ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers)) + " |"
    divider_line = "| " + " | ".join("-" * width for width in widths) + " |"
    body_lines = [
        "| " + " | ".join(str(value).ljust(widths[idx]) for idx, value in enumerate(row)) + " |"
        for row in rows
    ]
    return "\n".join([header_line, divider_line, *body_lines])


def write_report(campaign_summary: pd.DataFrame, channel_summary: pd.DataFrame, budget_plan: pd.DataFrame) -> None:
    total_spend = campaign_summary["spend"].sum()
    total_revenue = campaign_summary["revenue"].sum()
    total_gross_profit = campaign_summary["gross_profit"].sum()
    total_roi = (total_gross_profit - total_spend) / total_spend
    blended_cac = total_spend / campaign_summary["new_customers"].sum()

    scale_campaigns = campaign_summary[campaign_summary["recommendation"] == "Scale"].sort_values("roi", ascending=False)
    stop_campaigns = campaign_summary[campaign_summary["recommendation"] == "Stop"].sort_values("roi")
    best_channel = channel_summary.sort_values("roi", ascending=False).iloc[0]
    worst_channel = channel_summary.sort_values("roi").iloc[0]
    projected_profit_change = budget_plan["projected_profit_change"].sum()

    compact_campaign = campaign_summary[
        [
            "campaign_name",
            "channel",
            "spend",
            "new_customers",
            "cac",
            "roas",
            "roi",
            "net_profit_after_marketing",
            "recommendation",
            "decision_reason",
        ]
    ].sort_values(["recommendation", "roi"], ascending=[True, False])

    compact_channel = channel_summary[
        [
            "channel",
            "spend",
            "revenue",
            "new_customers",
            "cac",
            "roas",
            "roi",
            "net_profit_after_marketing",
            "budget_action",
        ]
    ].sort_values("roi", ascending=False)

    lines = [
        "# Marketing Campaign Performance + ROI Analysis Report",
        "",
        "## Executive Summary",
        "",
        f"The campaigns generated **{money(total_revenue)}** in revenue from **{money(total_spend)}** in marketing spend.",
        f"Blended CAC was **{money(blended_cac)}**, and total marketing ROI based on gross profit was **{pct(total_roi)}**.",
        f"The strongest channel is **{best_channel['channel']}** with ROI of **{pct(best_channel['roi'])}** and CAC of **{money(best_channel['cac'])}**.",
        f"The weakest channel is **{worst_channel['channel']}** with ROI of **{pct(worst_channel['roi'])}** and CAC of **{money(worst_channel['cac'])}**.",
        f"The budget reallocation scenario is estimated to change profit by **{money(projected_profit_change)}** over the analysis period.",
        "",
        "## Where To Invest More",
        "",
        dataframe_to_markdown(scale_campaigns[["campaign_name", "channel", "cac", "roas", "roi", "net_profit_after_marketing"]]),
        "",
        "## Campaigns To Stop",
        "",
        dataframe_to_markdown(stop_campaigns[["campaign_name", "channel", "cac", "roas", "roi", "net_profit_after_marketing", "decision_reason"]]),
        "",
        "## Campaign Performance",
        "",
        dataframe_to_markdown(compact_campaign),
        "",
        "## Channel Performance",
        "",
        dataframe_to_markdown(compact_channel),
        "",
        "## Budget Reallocation Plan",
        "",
        dataframe_to_markdown(budget_plan.sort_values("budget_change")),
        "",
        "## Business Recommendations",
        "",
        "1. Increase budget for campaigns with strong ROI and efficient CAC, especially high-intent search, affiliate, retargeting, and email.",
        "2. Stop or sharply reduce campaigns with negative ROI and high CAC, then only restart them with a new audience, offer, or creative hypothesis.",
        "3. Keep a small testing budget for awareness channels, but judge them separately from bottom-funnel conversion campaigns.",
        "4. Move reporting from campaign-level vanity metrics to CAC, ROAS, gross-profit ROI, and net profit after marketing.",
        "5. Review budget allocation weekly so spend follows performance instead of historical channel habits.",
        "",
        "## Resume Talking Point",
        "",
        "Built a marketing ROI analysis project using Python to evaluate CAC, ROAS, gross-profit ROI, channel performance, and campaign-level budget decisions, identifying which campaigns to scale, optimize, reduce, or stop.",
        "",
        "## Charts",
        "",
        "- `outputs/charts/roi_by_channel.png`",
        "- `outputs/charts/spend_vs_revenue_by_channel.png`",
        "- `outputs/charts/cac_by_campaign.png`",
        "- `outputs/charts/budget_reallocation.png`",
    ]

    (OUTPUT_DIR / "marketing_roi_report.md").write_text("\n".join(lines), encoding="utf-8")


def chart_as_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def html_table(df: pd.DataFrame) -> str:
    return df.to_html(index=False, border=0, classes="data-table", escape=True)


def write_html_report(campaign_summary: pd.DataFrame, channel_summary: pd.DataFrame, budget_plan: pd.DataFrame) -> None:
    total_spend = campaign_summary["spend"].sum()
    total_revenue = campaign_summary["revenue"].sum()
    total_gross_profit = campaign_summary["gross_profit"].sum()
    total_roi = (total_gross_profit - total_spend) / total_spend
    blended_cac = total_spend / campaign_summary["new_customers"].sum()
    projected_profit_change = budget_plan["projected_profit_change"].sum()

    best_channel = channel_summary.sort_values("roi", ascending=False).iloc[0]
    worst_channel = channel_summary.sort_values("roi").iloc[0]
    top_campaigns = campaign_summary.sort_values("roi", ascending=False).head(5)
    stop_campaigns = campaign_summary[campaign_summary["recommendation"] == "Stop"].sort_values("roi")

    campaign_view = campaign_summary[
        [
            "campaign_name",
            "channel",
            "spend",
            "new_customers",
            "cac",
            "roas",
            "roi",
            "net_profit_after_marketing",
            "recommendation",
            "decision_reason",
        ]
    ].sort_values(["recommendation", "roi"], ascending=[True, False])
    channel_view = channel_summary[
        [
            "channel",
            "spend",
            "revenue",
            "new_customers",
            "cac",
            "roas",
            "roi",
            "net_profit_after_marketing",
            "budget_action",
        ]
    ].sort_values("roi", ascending=False)

    chart_cards = [
        ("Marketing ROI by Channel", CHART_DIR / "roi_by_channel.png"),
        ("Spend vs Revenue by Channel", CHART_DIR / "spend_vs_revenue_by_channel.png"),
        ("Customer Acquisition Cost by Campaign", CHART_DIR / "cac_by_campaign.png"),
        ("Recommended Budget Reallocation", CHART_DIR / "budget_reallocation.png"),
    ]
    chart_html = "\n".join(
        f"""
        <section class="chart-card">
          <h3>{escape(title)}</h3>
          <img src="{chart_as_data_uri(path)}" alt="{escape(title)}">
        </section>
        """
        for title, path in chart_cards
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Marketing Campaign ROI Analysis Report</title>
  <style>
    :root {{
      --ink: #17212b;
      --muted: #5c6875;
      --line: #d9e0e7;
      --bg: #f6f8fa;
      --panel: #ffffff;
      --green: #247657;
      --red: #a6403a;
      --blue: #2f6f73;
      --gold: #b87528;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.5;
    }}
    header {{
      padding: 42px 6vw 34px;
      background: #12202c;
      color: #fff;
    }}
    header p {{ max-width: 920px; color: #d7e1ea; font-size: 18px; }}
    main {{ padding: 28px 6vw 48px; }}
    h1 {{ margin: 0 0 12px; font-size: 40px; letter-spacing: 0; }}
    h2 {{ margin: 34px 0 14px; font-size: 24px; }}
    h3 {{ margin: 0 0 12px; font-size: 17px; }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(150px, 1fr));
      gap: 14px;
      margin-top: -54px;
    }}
    .kpi, .section, .chart-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 8px 24px rgba(23, 33, 43, 0.06);
    }}
    .kpi {{ padding: 18px; }}
    .kpi span {{ color: var(--muted); font-size: 13px; font-weight: 700; text-transform: uppercase; }}
    .kpi strong {{ display: block; margin-top: 8px; font-size: 25px; }}
    .section {{ padding: 22px; margin-top: 18px; overflow-x: auto; }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(260px, 1fr));
      gap: 18px;
    }}
    .callout {{
      border-left: 4px solid var(--blue);
      padding: 12px 14px;
      background: #eef6f6;
      border-radius: 6px;
    }}
    .chart-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(280px, 1fr));
      gap: 18px;
    }}
    .chart-card {{ padding: 18px; }}
    .chart-card img {{ width: 100%; height: auto; display: block; }}
    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      background: #fff;
    }}
    .data-table th, .data-table td {{
      padding: 10px 11px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    .data-table th {{
      background: #eef2f5;
      font-size: 12px;
      text-transform: uppercase;
      color: #3f4d5a;
    }}
    footer {{ padding: 24px 6vw 42px; color: var(--muted); }}
    @media (max-width: 980px) {{
      .kpi-grid, .summary-grid, .chart-grid {{ grid-template-columns: 1fr; }}
      .kpi-grid {{ margin-top: 18px; }}
      h1 {{ font-size: 31px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Marketing Campaign Performance + ROI Analysis</h1>
    <p>Executive-ready analysis of CAC, ROAS, gross-profit ROI, channel performance, campaign decisions, and budget reallocation across Google, Facebook, Instagram, TikTok, Email, LinkedIn, and Affiliate.</p>
  </header>
  <main>
    <section class="kpi-grid">
      <div class="kpi"><span>Marketing Spend</span><strong>{money(total_spend)}</strong></div>
      <div class="kpi"><span>Revenue</span><strong>{money(total_revenue)}</strong></div>
      <div class="kpi"><span>Blended CAC</span><strong>{money(blended_cac)}</strong></div>
      <div class="kpi"><span>Gross-Profit ROI</span><strong>{pct(total_roi)}</strong></div>
      <div class="kpi"><span>Projected Profit Lift</span><strong>{money(projected_profit_change)}</strong></div>
    </section>

    <section class="section">
      <h2>Executive Summary</h2>
      <div class="summary-grid">
        <div class="callout">Best channel: <strong>{escape(best_channel["channel"])}</strong>, with ROI of <strong>{pct(best_channel["roi"])}</strong> and CAC of <strong>{money(best_channel["cac"])}</strong>.</div>
        <div class="callout">Weakest channel: <strong>{escape(worst_channel["channel"])}</strong>, with ROI of <strong>{pct(worst_channel["roi"])}</strong> and CAC of <strong>{money(worst_channel["cac"])}</strong>.</div>
      </div>
    </section>

    <section class="section">
      <h2>Top Campaigns To Scale</h2>
      {html_table(top_campaigns[["campaign_name", "channel", "cac", "roas", "roi", "net_profit_after_marketing", "recommendation"]])}
    </section>

    <section class="section">
      <h2>Campaigns To Stop</h2>
      {html_table(stop_campaigns[["campaign_name", "channel", "cac", "roas", "roi", "net_profit_after_marketing", "decision_reason"]])}
    </section>

    <h2>Charts</h2>
    <section class="chart-grid">
      {chart_html}
    </section>

    <section class="section">
      <h2>Channel Performance</h2>
      {html_table(channel_view)}
    </section>

    <section class="section">
      <h2>Campaign Performance</h2>
      {html_table(campaign_view)}
    </section>

    <section class="section">
      <h2>Budget Reallocation Scenario</h2>
      {html_table(budget_plan.sort_values("budget_change"))}
    </section>
  </main>
  <footer>
    Generated by the Python marketing ROI pipeline. Open the Streamlit app for interactive filtering and downloads.
  </footer>
</body>
</html>
"""
    (OUTPUT_DIR / "marketing_roi_report.html").write_text(html, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    data = generate_campaign_data()
    campaign_summary, channel_summary, budget_plan = summarize_performance(data)
    build_charts(campaign_summary, channel_summary, budget_plan)
    write_report(campaign_summary, channel_summary, budget_plan)
    write_html_report(campaign_summary, channel_summary, budget_plan)
    print("Marketing campaign ROI analysis complete.")
    print(f"Report: {OUTPUT_DIR / 'marketing_roi_report.md'}")
    print(f"HTML report: {OUTPUT_DIR / 'marketing_roi_report.html'}")
    print(f"Charts: {CHART_DIR}")


if __name__ == "__main__":
    main()
