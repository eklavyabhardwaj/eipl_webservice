# configurator/careers_api.py
from typing import List, Dict, Optional
import requests
import pandas as pd
from .models import ERPSettings  # admin-managed creds

JOB_OPENING_ENDPOINT   = "api/resource/Job Opening"
JOB_APPLICANT_ENDPOINT = "api/resource/Job Applicant"

def _get_erp():
    erp = ERPSettings.objects.first()
    if not erp or not erp.is_enabled:
        raise RuntimeError("ERP disabled or not configured in admin.")
    base = erp.base_url.rstrip("/")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"token {erp.api_key}:{erp.api_secret}",
    }
    return base, headers

def fetch_job_list() -> List[Dict]:
    try:
        base, headers = _get_erp()
        url = f"{base}/{JOB_OPENING_ENDPOINT}"
        params = {
            'fields': '["name","designation","status","territory","qualification"]',
            'limit_start': 0,
            'limit_page_length': 999999999
        }
        r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", [])
        df = pd.DataFrame(data)
        if not df.empty and "status" in df.columns:
            df = df[df["status"] == "Open"]
            return df.to_dict(orient="records")
        return []
    except Exception:
        return []

def fetch_job_details(job_id: str) -> Optional[Dict]:
    try:
        base, headers = _get_erp()
        url = f"{base}/{JOB_OPENING_ENDPOINT}/{job_id}"
        params = {
            'fields': '["name","description","custom_no_of_vacancy","territory","designation","qualification"]'
        }
        r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("data")
    except Exception:
        return None

def submit_applicant(payload: Dict, local_resume_path: Optional[str] = None) -> requests.Response:
    base, headers = _get_erp()

    # STEP 1: Upload the file to ERP, if provided
    if local_resume_path and os.path.exists(local_resume_path):
        with open(local_resume_path, 'rb') as f:
            upload_url = f"{base}/api/method/upload_file"
            upload_headers = {
                "Authorization": headers["Authorization"]
                # Do not include Content-Type when sending multipart/form-data
            }
            files = {
                "file": (os.path.basename(local_resume_path), f),
                "is_private": "0",  # public file (or set "1" for private)
            }

            try:
                resp = requests.post(upload_url, headers=upload_headers, files=files, timeout=20)
                resp.raise_for_status()
                file_url = resp.json().get("message", {}).get("file_url")
                if file_url:
                    payload["resume_attachment"] = file_url
            except Exception as e:
                print(f"[WARN] Resume upload failed: {e}")

    # STEP 2: Submit the application
    applicant_url = f"{base}/{JOB_APPLICANT_ENDPOINT}"
    return requests.post(applicant_url, headers=headers, json=payload, timeout=20)
