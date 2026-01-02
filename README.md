# Vendor Mass Email Sender

This program sends mass emails to vendors using a rotating pool of email accounts.

## Prerequisites

- Python 3.x
- Required packages: python-dotenv, requests, smtplib (built-in), csv (built-in), email (built-in), datetime (built-in), os (built-in)

## Setup

1. Ensure all files are in the same directory:
   - `main.py`
   - `job_activity_logger.py`
   - `setup_api.py`
   - `.env`
   - `email_accounts.json`
   - `vendoremails.csv`

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure API logging:
   ```bash
   python setup_api.py
   ```
   This will:
   - Ask for your WBL email/password and Employee ID (only on first run)
   - On subsequent runs, automatically use existing credentials from `.env`
   - Get your personal JWT Token
   - Update your `.env` file automatically

4. Configure your environment variables in `.env`:
   - `EMAIL_ACCOUNTS_FILE=email_accounts.json`
   - `SMTP_SERVER=smtp.gmail.com`
   - `SMTP_PORT=587`
   - `REPLY_TO_EMAIL=your-reply-email@example.com`
   - `WBL_EMAIL=your-wbl-email@example.com` (for API login)
   - `WBL_PASSWORD=your-wbl-password` (for API login)

5. Update `email_accounts.json` with your email accounts in the format:
   ```json
   [
     {
       "EMAIL_USER": "your-email@gmail.com",
       "EMAIL_PASS": "your-app-password"
     }
   ]
   ```

6. Add vendor emails to `vendoremails.csv` (one email per row under 'email' column)

7. Optionally, place your resume PDF as `Hemalatha.pdf` in the directory for attachment

## Running the Program

```bash
python main.py
```

## Expected Output

- The program will cycle through email accounts (up to 100 emails per account)
- Logs total sent email count to WBL API job activity table
- Creates detailed log file in `logs/` directory with timestamps and status for each email
- Prints sending status for each email
- Warns if PDF attachment is missing (but continues sending)

## Notes

- Uses Gmail SMTP by default
- Automatically switches accounts when limit is reached
- Skips invalid emails
- Resume attachment is optional
