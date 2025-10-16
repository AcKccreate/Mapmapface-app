import os
import pandas as pd
import sys
import os
# Ensure repo root is on sys.path so config can be imported
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from config import EMAIL_RECIPIENTS

SCORES_PATH = "app/data/processed/scores_latest.csv"
TOP_N = int(os.environ.get("DIGEST_TOP_N", "20"))
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL = os.environ.get("MAIL_FROM", "locum-agent@yourdomain.com")


def load_scores():
    df = pd.read_csv(SCORES_PATH)
    # Return top-N per specialty combined
    out = []
    for spec in ["HO", "PDH"]:
        d = df[df.get('specialty') == spec].sort_values('score', ascending=False).head(TOP_N)
        out.append(d)
    if out:
        return pd.concat(out, ignore_index=True)
    return df


def build_email_body(df: pd.DataFrame) -> str:
    rows = df.to_dict(orient="records")
    html = "<h3>Top Facilities Likely to Need Locum Coverage</h3><ul>"
    for row in rows:
        name = row.get('facility_name') or row.get('Facility Name') or row.get('facility')
        city = row.get('city','')
        state = row.get('state','')
        spec = row.get('specialty','')
        score = float(row.get('score',0))
        html += f"<li><b>{name}</b> in {city}, {state} — {spec} (score: {score:.2f})</li>"
    html += "</ul>"
    return html


def send_email(html_body: str):
    if not SENDGRID_API_KEY:
        raise ValueError("Missing SENDGRID_API_KEY")
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=EMAIL_RECIPIENTS,
        subject="Daily Locum Need Digest",
        html_content=html_body,
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    resp = sg.send(message)
    return resp.status_code


def main():
    df = load_scores()
    body = build_email_body(df)
    status = send_email(body)
    print(f"Sent via SendGrid, status: {status}")


if __name__ == '__main__':
    main()
