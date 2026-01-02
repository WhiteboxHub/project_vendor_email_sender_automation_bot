#vendor emails


import json
import smtplib
import os
import csv
import logging
import time
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
from datetime import datetime
from job_activity_logger import JobActivityLogger

# Load environment variables
load_dotenv()

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename=f"logs/email_sender_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load email accounts from JSON file
with open(os.getenv("EMAIL_ACCOUNTS_FILE"), 'r') as f:
    email_accounts = json.load(f)

current_account_index = 0
emails_sent_with_current_account = 0
MAX_EMAILS_PER_ACCOUNT = 100
PROGRESS_FILE = "last_index.txt"

SMTP_HOST = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
REPLY_TO_EMAIL = os.getenv("REPLY_TO_EMAIL")

# Path to resume PDF
RESUME_PATH = "Sai_madhavi.pdf"  # Place your PDF file here

# Subject and Body
subject = "AI Engineer | USC "

text_body = """Hi,

I’m an AI Engineer with experience building production-grade Agentic AI and RAG systems. I’ve worked on large-scale GenAI platforms with multi-agent orchestration, memory systems, secure tool use, and cloud-native deployment.

Highlights:

Agentic AI with LangGraph and MCP, including stateful memory and secure tool execution

End-to-end RAG pipelines using Milvus, LangChain, FastAPI

LLM evaluation and observability (Precision@K/Recall@K, Prometheus, Grafana)

Cloud deployment on AWS (EKS, Bedrock, SageMaker) and GCP (Cloud Run, Compute Engine)

MLOps, CI/CD, monitoring, and Kubernetes-based inference

I’m immediately available and happy to share my resume or discuss opportunities.

Best regards,
    Sai_madhavi
📍 Pleasanton, CA
📧 saimadhavi.ip@gmail.com

🔗 LinkedIn: https://www.linkedin.com/in/sai-madhavi/
"""

def get_next_email_account(force_switch=False):
    global current_account_index, emails_sent_with_current_account
    if force_switch or emails_sent_with_current_account >= MAX_EMAILS_PER_ACCOUNT:
        current_account_index = (current_account_index + 1) % len(email_accounts)
        emails_sent_with_current_account = 0
        print(f"\nSwitching to email account: {email_accounts[current_account_index]['EMAIL_USER']}\n")
    account = email_accounts[current_account_index]
    emails_sent_with_current_account += 1
    return account


def send_email(to_email):
    account = get_next_email_account()

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = "Sai madhavi <saimadhavi.ip@gmail.com>"
    msg["To"] = to_email
    msg["Reply-To"] = REPLY_TO_EMAIL

    # Attach body
    msg.attach(MIMEText(text_body, "plain"))

    # Attach resume PDF
    if os.path.exists(RESUME_PATH):
        with open(RESUME_PATH, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(RESUME_PATH))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(RESUME_PATH)}"'
        msg.attach(part)
    else:
        print(f"⚠ Resume file not found: {RESUME_PATH}")

    # Send the email
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(account["EMAIL_USER"], account["EMAIL_PASS"])
        server.send_message(msg)

    return account["EMAIL_USER"]

# 🔹 Fetch emails from CSV file
def fetch_vendor_emails():
    EMAIL_CSV = "vendoremails.csv"  # Your CSV file in the same directory
    emails = []
    total_rows = 0
    if os.path.exists(EMAIL_CSV):
        with open(EMAIL_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                email = row.get("Email", "").strip()
                if email:  # skip empty emails
                    emails.append(email)
                else:
                    print(f"DEBUG: Skipping row {total_rows} - No email found in 'Email' column")
        print(f"DEBUG: Processed {total_rows} total rows, found {len(emails)} valid emails.")
    else:
        print(f"⚠ CSV file not found: {EMAIL_CSV}")
    return emails

def run():
    print("Starting email campaign...")
    logging.info("Starting email campaign")
    activity_logger = JobActivityLogger()
    vendor_emails = fetch_vendor_emails()  # All emails from CSV
    print(f"Loaded {len(vendor_emails)} emails from CSV")
    logging.info(f"Loaded {len(vendor_emails)} emails from CSV")
    
    if len(vendor_emails) == 0:
        print("⚠️ No emails found in CSV file. Exiting.")
        return

    # Resume logic
    start_index = 0
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                start_index = int(f.read().strip())
            print(f"Resuming from index {start_index}")
        except:
            start_index = 0
    
    sent_count = 0
    for i in range(start_index, len(vendor_emails)):
        email = vendor_emails[i]
        try:
            sender_email = send_email(email)
            sent_count += 1
            logging.info(f"SUCCESS: Sent to {email} using {sender_email}")
            print(f"✅ Sent to {email} using {sender_email}")
            
            # Save progress
            with open(PROGRESS_FILE, "w") as f:
                f.write(str(i + 1))
            
            # Random delay between 5 to 15 seconds
            time.sleep(random.uniform(5, 15))
            
        except smtplib.SMTPResponseException as e:
            error_code = e.smtp_code
            error_msg = e.smtp_error.decode('utf-8', errors='ignore')
            if error_code == 550 or "limit exceeded" in error_msg.lower():
                print(f"⚠️ Limit reached for {email_accounts[current_account_index]['EMAIL_USER']}. Switching...")
                get_next_email_account(force_switch=True)
                # Retry the same email with the new account
                try:
                    sender_email = send_email(email)
                    sent_count += 1
                    print(f"✅ Sent to {email} using {sender_email} (after switch)")
                    with open(PROGRESS_FILE, "w") as f:
                        f.write(str(i + 1))
                except Exception as retry_e:
                    print(f"❌ Failed even after switch: {retry_e}")
            else:
                print(f"❌ SMTP Error: {e}")
        except Exception as e:
            logging.error(f"FAILED: Could not send to {email} - {str(e)}")
            print(f"❌ Failed to send to {email}: {e}")

    logging.info(f"Campaign completed: {sent_count} successful sends out of {len(vendor_emails)} attempts")

    # Log total sent emails to API
    if sent_count > 0:
        print(f"\nLogging activity to WBL backend...")
        activity_logger.log_activity(
            activity_count=sent_count,
            notes=f"Vendor email campaign completed. Sent {sent_count} emails."
        )
        logging.info(f"API logging completed for {sent_count} emails")

if __name__ == "__main__":
    run()
