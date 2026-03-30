"""
Sends the morning reading list email via Gmail SMTP.

Requires env vars:
  GMAIL_ADDRESS      — your Gmail address (send + receive)
  GMAIL_APP_PASSWORD — Gmail App Password (not your account password)
  PAGES_URL          — full GitHub Pages URL for the reading list
"""

import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send(pages_url: str, date: datetime | None = None) -> None:
    gmail_address = os.environ.get("GMAIL_ADDRESS", "")
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient_2 = os.environ.get("RECIPIENT_EMAIL_2", "")

    if not gmail_address or not app_password:
        print("[mailer] GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set — skipping email")
        return

    if date is None:
        date = datetime.now(tz=timezone.utc)

    date_str = date.strftime("%-d %B %Y")
    subject = f"The Daily — {date_str}"

    # Plain text fallback
    text_body = f"Your morning reading list is ready.\n\n{pages_url}\n"

    # Minimal HTML email — matches the SPA aesthetic
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    background: #ffffff;
    color: #111111;
    margin: 0;
    padding: 40px 0;
  }}
  .wrap {{
    max-width: 480px;
    margin: 0 auto;
    padding: 0 24px;
  }}
  .label {{
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #999999;
    font-family: 'Courier New', Courier, monospace;
    margin-bottom: 24px;
  }}
  h1 {{
    font-size: 22px;
    font-weight: 500;
    letter-spacing: -0.01em;
    margin: 0 0 16px 0;
    line-height: 1.3;
  }}
  p {{
    font-size: 14px;
    color: #555555;
    font-family: 'Courier New', Courier, monospace;
    line-height: 1.7;
    margin: 0 0 28px 0;
  }}
  a.cta {{
    display: inline-block;
    font-size: 13px;
    color: #111111;
    text-decoration: none;
    border-bottom: 1px solid #111111;
    padding-bottom: 2px;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    letter-spacing: 0.02em;
  }}
  .footer {{
    margin-top: 48px;
    font-size: 11px;
    color: #cccccc;
    font-family: 'Courier New', Courier, monospace;
  }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="label">{date_str}</div>
    <h1>The Daily</h1>
    <p>10 articles from The Economist, LRB, NLR,<br>RNZ, and Substack.</p>
    <a class="cta" href="{pages_url}">Open reading list &rarr;</a>
    <div class="footer">daily-reader &middot; delivered at 7am</div>
  </div>
</body>
</html>"""

    recipients = [r for r in [gmail_address, recipient_2] if r]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, app_password)
        server.sendmail(gmail_address, recipients, msg.as_string())

    print(f"[mailer] Email sent to {', '.join(recipients)}")
