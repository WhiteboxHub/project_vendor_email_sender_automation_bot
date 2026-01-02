import requests
from datetime import date
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class JobActivityLogger:

    def __init__(self):
        self.api_url = os.getenv('WBL_API_URL', '')
        self.api_token = os.getenv('WBL_API_TOKEN', '')
        self.wbl_email = os.getenv('WBL_EMAIL', '')
        self.wbl_password = os.getenv('WBL_PASSWORD', '')
        self.job_unique_id = os.getenv('JOB_UNIQUE_ID', 'vendors_mass_email_sender')
        self.employee_id = int(os.getenv('EMPLOYEE_ID', '411'))
        self.selected_candidate_id = int(os.getenv('SELECTED_CANDIDATE_ID', '570'))

        # Auto-login if token is missing
        if not self.api_token:
            if self.wbl_email and self.wbl_password:
                self._auto_login()
            else:
                print("  WARNING: WBL_API_TOKEN not set and WBL_EMAIL/WBL_PASSWORD not configured. Activity logging will fail.")

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def save_vendor_contact(self, data: dict) -> bool:
        """Save vendor contact to API (if needed for email recipients)"""
        if not self.api_token:
            return False

        base_url = self.api_url.rstrip('/')
        if not self.api_url.endswith('/api'):
            base_url = f"{self.api_url}/api"

        endpoint = f"{base_url}/vendor_contact"

        payload = {
            "full_name": data.get('full_name') or 'Unknown',
            "email": data.get('email'),
            "phone": data.get('phone'),
            "linkedin_id": data.get('linkedin_id'),
            "company_name": data.get('company_name'),
            "location": data.get('location'),
            "source_email": os.getenv('EMAIL_USER')  # From email account used
        }

        try:
            response = requests.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to save vendor contact: {e}")
            return False

    def log_activity(
        self,
        activity_count: int,
        notes: str = "",
        candidate_id: int = 0,
        activity_date: Optional[str] = None
    ) -> bool:
        """Log activity to job activity table"""
        if not self.api_token:
            print(" Cannot log activity: No API token configured")
            return False

        if activity_date is None:
            activity_date = date.today().isoformat()

        if candidate_id == 0 and self.selected_candidate_id != 0:
            candidate_id = self.selected_candidate_id

        job_type_id = self._get_job_type_id()
        if job_type_id is None:
            print(" Cannot log activity: Job type not found")
            return False

        payload = {
            "job_id": job_type_id,
            "employee_id": self.employee_id,
            "activity_count": activity_count,
            "candidate_id": candidate_id if candidate_id != 0 else None,
            "notes": notes,
            "activity_date": activity_date
        }

        base_url = self.api_url.rstrip('/')
        if not self.api_url.endswith('/api'):
            base_url = f"{self.api_url}/api"

        endpoint = f"{base_url}/job_activity_logs"

        # Try up to 2 times: initial + retry after token refresh
        for attempt in range(2):
            try:
                response = requests.post(endpoint, json=payload, headers=self.headers)
                if response.status_code == 401 and attempt == 0:
                    # Token might be expired, try to refresh
                    self._auto_login()
                    # Update headers with new token
                    self.headers = {
                        "Authorization": f"Bearer {self.api_token}",
                        "Content-Type": "application/json"
                    }
                    continue  # Retry with new token

                response.raise_for_status()
                result = response.json()
                print(f" Activity logged: {activity_count} emails sent (Activity ID: {result.get('id', 'N/A')})")
                return True
            except requests.exceptions.RequestException as e:
                if attempt == 0 and hasattr(e, 'response') and e.response and e.response.status_code == 401:
                    # Try refresh on 401
                    self._auto_login()
                    self.headers = {
                        "Authorization": f"Bearer {self.api_token}",
                        "Content-Type": "application/json"
                    }
                    continue
                print(f" Failed to log activity: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_detail = e.response.json()
                        print(f"   Error details: {error_detail}")
                    except:
                        print(f"   Response: {e.response.text}")
                return False
        return False

    def _auto_login(self) -> None:
        """Automatically login and get token using stored credentials"""
        if not (self.wbl_email and self.wbl_password):
            print("  Cannot auto-login: WBL_EMAIL or WBL_PASSWORD not configured")
            return

        print("  Auto-logging in to WBL API...")
        login_url = f"{self.api_url}/login"
        if "localhost" in self.api_url and not self.api_url.endswith("/api"):
            login_url = f"{self.api_url}/api/login"

        try:
            response = requests.post(
                login_url,
                data={
                    "username": self.wbl_email,
                    "password": self.wbl_password
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            data = response.json()
            token = data.get("access_token")

            if token:
                # Update .env file
                self._update_env_token(token)
                self.api_token = token
                print(f"  Token obtained and saved: {token[:20]}...")
            else:
                print("  ERROR: No access_token in login response")

        except Exception as e:
            print(f"  Auto-login failed: {e}")

    def _update_env_token(self, token: str) -> None:
        """Update the WBL_API_TOKEN in .env file"""
        env_file = ".env"
        try:
            with open(env_file, 'r') as f:
                content = f.read()

            # Replace or add the token
            if "WBL_API_TOKEN=" in content:
                content = content.replace(f"WBL_API_TOKEN={os.getenv('WBL_API_TOKEN', '')}", f"WBL_API_TOKEN={token}")
            else:
                content += f"\nWBL_API_TOKEN={token}\n"

            with open(env_file, 'w') as f:
                f.write(content)
        except Exception as e:
            print(f"  Failed to update .env with token: {e}")

    def _get_job_type_id(self) -> Optional[int]:
        base_url = self.api_url.rstrip('/')
        if not self.api_url.endswith('/api'):
            base_url = f"{self.api_url}/api"

        endpoint = f"{base_url}/job-types"

        # Try up to 2 times: initial + retry after token refresh
        for attempt in range(2):
            try:
                response = requests.get(endpoint, headers=self.headers)
                if response.status_code == 401 and attempt == 0:
                    # Token might be expired, try to refresh
                    self._auto_login()
                    # Update headers with new token
                    self.headers = {
                        "Authorization": f"Bearer {self.api_token}",
                        "Content-Type": "application/json"
                    }
                    continue  # Retry with new token

                response.raise_for_status()
                job_types = response.json()

                # Find matching job type
                for job_type in job_types:
                    if job_type.get('unique_id') == self.job_unique_id:
                        return job_type.get('id')

                print(f"WARNING: Job type '{self.job_unique_id}' not found in database")
                return None
            except Exception as e:
                if attempt == 0 and "401" in str(e):
                    # Try refresh on 401
                    self._auto_login()
                    self.headers = {
                        "Authorization": f"Bearer {self.api_token}",
                        "Content-Type": "application/json"
                    }
                    continue
                print(f"WARNING: Could not fetch job type ID: {e}")
                return None
        return None


# Convenience function for simple usage
def log_job_activity(count: int, notes: str = "") -> bool:
    logger = JobActivityLogger()
    return logger.log_activity(count, notes)
