import requests
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── Configuration ────────────────────────────────────────────────────────────
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "JPM", "V", "BRK.B"]
TD_KEY         = os.environ["TD_API_KEY"]
EMAIL_SENDER   = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECEIVER = os.environ["EMAIL_RECEIVER"]
OUTPUT_FILE    = "docs/index.html"
TD_BASE        = "https://api.twelvedata.com"


# ── Fetch Data ────────────────────────────────────────────────────────────────
def fetch_data(tickers):
    """Fetch quotes and 7-day history in batch calls (2 API requests total)."""
    symbols = ",".join(tickers)

    # Batch quote — 1 request for all tickers
    print("  Fetching quotes...")
    q_resp = requests.get(f"{TD_BASE}/quote", params={
        "symbol": symbols, "apikey": TD_KEY
    }, timeout=15).json()

    # Batch time series — 1 request for all tickers
    print("  Fetching sparklines...")
    ts_raw  = requests.get(f"{TD_BASE}/time_series", params={
        "symbol": symbols, "interval": "1day", "outputsize": 7, "apikey": TD_KEY
    }, timeout=15)
    ts_resp = ts_raw.json()
    print(f"  DEBUG ts_resp keys: {list(ts_resp.keys())[:5]}")
    print(f"  DEBUG ts_resp sample: {str(ts_resp)[:300]}")

    stocks = []
    for ticker in tickers:
        try:
            q  = q_resp.get(ticker, {})
            ts = ts_resp.get(ticker, {})
            print(f"  DEBUG {ticker} ts keys: {list(ts.keys()) if isinstance(ts, dict) else type(ts)}")
            if q.get("status") == "error" or ts.get("status") == "error":
                print(f"  ⚠️  Skipping {ticker} — {q.get('message', 'unknown error')}")
                continue
            closes = [round(float(v["close"]), 2) for v in reversed(ts["values"])]
            stocks.append({
                "ticker":     ticker,
                "price":      round(float(q["close"]), 2),
                "change":     round(float(q["change"]), 2),
                "change_pct": round(float(q["percent_change"]), 2),
                "prices":     closes,
            })
        except Exception as e:
            print(f"  ⚠️  Skipping {ticker} — {e}")
    return stocks


# ── Build Sparkline SVG ───────────────────────────────────────────────────────
def sparkline(prices, color, width=120, height=40):
    if len(prices) < 2:
        return ""
    mn, mx = min(prices), max(prices)
    rng = mx - mn or 1
    pts = []
    for i, p in enumerate(prices):
        x = i * width / (len(prices) - 1)
        y = height - ((p - mn) / rng) * height
        pts.append(f"{x:.1f},{y:.1f}")
    return (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}">'
        f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linejoin="round"/>'
        f'</svg>'
    )


# ── Build HTML ────────────────────────────────────────────────────────────────
def build_html(stocks):
    updated = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    cards = ""
    for s in stocks:
        color = "#16a34a" if s["change"] >= 0 else "#dc2626"
        arrow = "▲" if s["change"] >= 0 else "▼"
        spark = sparkline(s["prices"], color)
        sign  = "+" if s["change"] >= 0 else ""
        cards += f"""
        <div class="card">
          <div class="ticker">{s['ticker']}</div>
          <div class="price">${s['price']:,.2f}</div>
          <div class="change" style="color:{color}">
            {arrow} {sign}{s['change']:,.2f} ({sign}{s['change_pct']:.2f}%)
          </div>
          <div class="spark">{spark}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Portfolio Dashboard</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f9fafb; color: #111; padding: 2rem; }}
    h1   {{ font-size: 1.5rem; font-weight: 600; margin-bottom: 0.25rem; }}
    .sub {{ color: #6b7280; font-size: 0.85rem; margin-bottom: 2rem; }}
    .grid {{ display: grid;
             grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
             gap: 1rem; }}
    .card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
             padding: 1.25rem; display: flex; flex-direction: column; gap: 0.3rem;
             box-shadow: 0 1px 3px rgba(0,0,0,.06); }}
    .ticker {{ font-weight: 700; font-size: 1rem; letter-spacing: .03em; }}
    .price  {{ font-size: 1.4rem; font-weight: 600; }}
    .change {{ font-size: 0.85rem; font-weight: 500; }}
    .spark  {{ margin-top: 0.5rem; }}
  </style>
</head>
<body>
  <h1>📈 Portfolio Dashboard</h1>
  <p class="sub">Updated: {updated} &nbsp;·&nbsp; 7-day sparklines</p>
  <div class="grid">{cards}</div>
</body>
</html>"""


# ── Send Email ────────────────────────────────────────────────────────────────
def send_email(html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📈 Portfolio Update — {datetime.now().strftime('%b %d, %Y')}"
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVER
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(EMAIL_SENDER, EMAIL_PASSWORD)
        srv.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
    print("✅ Email sent.")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    print("Fetching stock data...")
    stocks = fetch_data(TICKERS)
    if not stocks:
        print("❌ No stock data fetched. Aborting.")
        exit(1)
    html = build_html(stocks)
    with open(OUTPUT_FILE, "w") as f:
        f.write(html)
    print(f"✅ HTML saved to {OUTPUT_FILE}")
    send_email(html)
