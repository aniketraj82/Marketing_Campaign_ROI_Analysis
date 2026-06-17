# Marketing Campaign Performance + ROI Analysis

Portfolio-ready marketing analytics project that answers one practical business question:

**Which campaigns actually work, where should budget increase, and which campaigns should be stopped?**

## What This Project Covers

- Customer Acquisition Cost (CAC)
- Return on ad spend (ROAS)
- Marketing ROI based on gross profit
- Channel performance across Google, Facebook, Instagram, TikTok, Email, LinkedIn, and Affiliate
- Campaign-level stop / optimize / scale recommendations
- Budget reallocation scenario
- Executive-ready report and Streamlit dashboard

## Project Structure

```text
Marketing_Campaign_ROI_Analysis/
  .streamlit/
    config.toml
  app.py
  Procfile
  requirements.txt
  runtime.txt
  data/
    marketing_campaign_data.csv
  outputs/
    marketing_roi_report.md
    marketing_roi_report.html
    campaign_performance_summary.csv
    channel_performance_summary.csv
    budget_reallocation_plan.csv
    charts/
  src/
    marketing_campaign_roi_analysis.py
```

## How To Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate the dataset, charts, recommendations, and report:

```bash
python src/marketing_campaign_roi_analysis.py
```

Launch the dashboard:

```bash
streamlit run app.py
```

The dashboard auto-generates missing pipeline outputs on first launch. Use the sidebar button to refresh the generated data, CSV summaries, charts, Markdown report, and standalone HTML report.

## Deploy

This project is ready for Streamlit Community Cloud, Render, Railway, or any platform that can run a Python web process.

### Streamlit Community Cloud

1. Push this folder to GitHub.
2. Create a new Streamlit app.
3. Set the main file path to `app.py`.
4. Deploy. Streamlit installs `requirements.txt` and uses `.streamlit/config.toml`.

### Render / Railway / Heroku-style process

Use the included `Procfile`:

```bash
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

## Outputs

- `outputs/marketing_roi_report.html`: standalone executive report with embedded charts.
- `outputs/marketing_roi_report.md`: Markdown report for GitHub and interview review.
- `outputs/campaign_performance_summary.csv`: campaign-level CAC, ROAS, ROI, and recommendations.
- `outputs/channel_performance_summary.csv`: channel-level performance across Google, Facebook, Instagram, TikTok, Email, LinkedIn, and Affiliate.
- `outputs/budget_reallocation_plan.csv`: recommended budget changes and projected profit impact.

## Business Story

The project uses a realistic synthetic dataset for an ecommerce company running paid and owned marketing campaigns. It calculates CAC, ROAS, ROI, conversion efficiency, and gross profit by campaign and channel, then recommends which campaigns deserve more budget and which should be paused.

## Resume Talking Point

Built a Python marketing analytics project to evaluate campaign CAC, ROAS, ROI, channel efficiency, and budget reallocation opportunities, identifying campaigns to scale, optimize, or stop.
