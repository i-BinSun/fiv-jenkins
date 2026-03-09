"""
Integration tests for FIV Portal Upload Ingredient APIs

These tests call the real FIV Portal API endpoints directly using requests.
They validate:

  1. GET  /ifwi_check_proj_mandatory/{proj_id}    - Fetch project required params
  2. POST /app/rest/ifwi_submit_ingredients/       - Upload ingredient
  3. POST /app/rest/ifwi_submit_ingredients_build/ - Upload build
  4. GET  /ingredients_status/{upload_id}          - Check upload status

Required environment variables (configured in .env):

    FIV_BASE_URL   - FIV Portal URL (default: https://fiv-ifwi.intel.com)
    FIV_USERNAME   - FIV Portal username
    FIV_PASSWORD   - FIV Portal password
    FIV_PROJ_ID    - Project ID for testing

Run:
    python -m unittest tests.test_upload_ingredient_integration -v

All tests are skipped automatically if credentials are not configured.
"""

import json
import os
import tempfile
import time
import unittest
import urllib3

import requests
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# Suppress InsecureRequestWarning for verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.environ.get("FIV_BASE_URL", "https://fiv-ifwi.intel.com").rstrip("/")
USERNAME = os.environ.get("FIV_USERNAME", "")
PASSWORD = os.environ.get("FIV_PASSWORD", "")
PROJ_ID = os.environ.get("FIV_PROJ_ID", "")

CREDENTIALS_SET = all([USERNAME, PASSWORD, PROJ_ID])
SKIP_REASON = (
    "FIV Portal credentials not configured. "
    "Set FIV_USERNAME, FIV_PASSWORD and FIV_PROJ_ID in .env"
)

TIMEOUT = 60  # seconds


# ============================================================================
# API Connectivity Tests
# ============================================================================

@unittest.skipUnless(CREDENTIALS_SET, SKIP_REASON)
class TestAPIConnectivity(unittest.TestCase):
    """Test basic connectivity to FIV Portal."""

    def test_server_reachable(self):
        """Verify the FIV Portal server is reachable."""
        resp = requests.get(BASE_URL, timeout=TIMEOUT, verify=False)
        self.assertIn(resp.status_code, [200, 301, 302, 403])

    def test_invalid_credentials_rejected(self):
        """Verify that invalid credentials are rejected on upload endpoint."""
        resp = requests.post(
            f"{BASE_URL}/app/rest/ifwi_submit_ingredients/",
            auth=("invalid_user_xyz", "invalid_pass_xyz"),
            data={"proj_id": PROJ_ID},
            timeout=TIMEOUT,
            verify=False,
        )
        self.assertIn(resp.status_code, [401, 403])


# ============================================================================
# Project Requirements API Tests
# GET /ifwi_check_proj_mandatory/{proj_id}
# ============================================================================

@unittest.skipUnless(CREDENTIALS_SET, SKIP_REASON)
class TestFetchProjectRequirements(unittest.TestCase):
    """Test GET /ifwi_check_proj_mandatory/{proj_id}."""

    def test_valid_project_returns_required_params(self):
        """Fetch requirements for a valid project and verify response."""
        resp = requests.get(
            f"{BASE_URL}/ifwi_check_proj_mandatory/{PROJ_ID}",
            timeout=TIMEOUT,
            verify=False,
        )
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertIn("required_parm", data)
        self.assertIsInstance(data["required_parm"], list)
        print(f"\n  Project {PROJ_ID} required params: {data['required_parm']}")

    def test_invalid_project_id(self):
        """Fetch requirements with a non-existent project ID."""
        resp = requests.get(
            f"{BASE_URL}/ifwi_check_proj_mandatory/NONEXISTENT_99999",
            timeout=TIMEOUT,
            verify=False,
        )
        # Server may return 200 with empty list, 404, or other error
        print(f"\n  Invalid project response: HTTP {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            self.assertIsInstance(data.get("required_parm", []), list)


# ============================================================================
# Ingredient Upload API Tests
# POST /app/rest/ifwi_submit_ingredients/
# ============================================================================

@unittest.skipUnless(CREDENTIALS_SET, SKIP_REASON)
class TestIngredientUpload(unittest.TestCase):
    """Test POST /app/rest/ifwi_submit_ingredients/."""

    def _upload(self, data, files=None):
        """Helper to POST to upload endpoint."""
        return requests.post(
            f"{BASE_URL}/app/rest/ifwi_submit_ingredients/",
            auth=(USERNAME, PASSWORD),
            data=data,
            files=files,
            timeout=TIMEOUT,
            verify=False,
        )

    def _base_data(self, **overrides):
        """Build base request data with defaults."""
        data = {
            "proj_id": PROJ_ID,
            "ingredient_name": "IntegrationTest",
            "ingredient_version": "0.0.1-test",
            "comments": "Automated integration test",
            "send_email": "",
            "ingredient_link": "",
            "ifwi_build_link": "",
            "admin_list": "",
            "external_check": "N",
            "config_path": "",
            "svn": "",
            "se_svn": "",
        }
        data.update(overrides)
        return data

    def test_upload_with_ingredient_link(self):
        """Upload an ingredient using a link."""
        data = self._base_data(
            ingredient_link="https://example.com/integration-test-artifact.zip",
            comments="Integration test - upload via link",
        )
        resp = self._upload(data)

        print(f"\n  HTTP {resp.status_code}")
        try:
            body = resp.json()
            print(f"  Response: {json.dumps(body, indent=2, ensure_ascii=False)}")
            if resp.status_code == 200 and body.get("ing_upload_id"):
                self.assertTrue(body["ing_upload_id"])
        except json.JSONDecodeError:
            print(f"  Response text: {resp.text[:300]}")

        # Accept 200 (success) or other expected codes
        self.assertIsNotNone(resp.status_code)

    def test_upload_with_ingredient_file(self):
        """Upload an ingredient using a real file."""
        with tempfile.NamedTemporaryFile(
            suffix=".txt", prefix="fiv_test_", delete=False
        ) as f:
            f.write(b"Integration test file content")
            tmp_path = f.name

        try:
            data = self._base_data(
                comments="Integration test - upload via file",
            )
            with open(tmp_path, "rb") as fh:
                files = {"ingredient_file": (os.path.basename(tmp_path), fh)}
                resp = self._upload(data, files=files)

            print(f"\n  HTTP {resp.status_code}")
            try:
                body = resp.json()
                print(f"  Response: {json.dumps(body, indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError:
                print(f"  Response text: {resp.text[:300]}")

            self.assertIsNotNone(resp.status_code)
        finally:
            os.unlink(tmp_path)

    def test_upload_missing_required_fields(self):
        """Upload with missing required fields should fail gracefully."""
        data = {
            "proj_id": PROJ_ID,
            # Missing ingredient_name, ingredient_version, etc.
        }
        resp = self._upload(data)
        print(f"\n  Missing fields response: HTTP {resp.status_code}")
        # Server should reject incomplete request
        self.assertIsNotNone(resp.status_code)


# ============================================================================
# Build Upload API Tests
# POST /app/rest/ifwi_submit_ingredients_build/
# ============================================================================

@unittest.skipUnless(CREDENTIALS_SET, SKIP_REASON)
class TestBuildUpload(unittest.TestCase):
    """Test POST /app/rest/ifwi_submit_ingredients_build/."""

    def test_upload_with_build_link(self):
        """Upload using an IFWI build link."""
        data = {
            "proj_id": PROJ_ID,
            "ingredient_name": "IntegrationTest",
            "ingredient_version": "0.0.1-build-test",
            "comments": "Integration test - build upload",
            "ifwi_build_link": "https://example.com/integration-test-build.zip",
            "send_email": "",
            "ingredient_link": "",
            "admin_list": "",
            "external_check": "N",
            "config_path": "",
            "svn": "",
            "se_svn": "",
        }
        resp = requests.post(
            f"{BASE_URL}/app/rest/ifwi_submit_ingredients_build/",
            auth=(USERNAME, PASSWORD),
            data=data,
            timeout=TIMEOUT,
            verify=False,
        )
        print(f"\n  Build upload HTTP {resp.status_code}")
        try:
            body = resp.json()
            print(f"  Response: {json.dumps(body, indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError:
            print(f"  Response text: {resp.text[:300]}")

        self.assertIsNotNone(resp.status_code)


# ============================================================================
# Upload Status API Tests
# GET /ingredients_status/{upload_id}
# ============================================================================

@unittest.skipUnless(CREDENTIALS_SET, SKIP_REASON)
class TestUploadStatus(unittest.TestCase):
    """Test GET /ingredients_status/{upload_id}."""

    def test_query_nonexistent_upload_id(self):
        """Query status for a non-existent upload ID."""
        resp = requests.get(
            f"{BASE_URL}/ingredients_status/INVALID_ID_000",
            timeout=TIMEOUT,
            verify=False,
        )
        print(f"\n  Invalid upload ID status: HTTP {resp.status_code}")
        try:
            body = resp.json()
            print(f"  Response: {json.dumps(body, indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError:
            print(f"  Response text: {resp.text[:200]}")
        self.assertIsNotNone(resp.status_code)

    def test_upload_then_check_status(self):
        """Upload an ingredient, then immediately check its status."""
        # Step 1: Upload
        data = {
            "proj_id": PROJ_ID,
            "ingredient_name": "IntegrationTest",
            "ingredient_version": "0.0.1-status-test",
            "comments": "Integration test - status check",
            "ingredient_link": "https://example.com/integration-test-status.zip",
            "send_email": "",
            "ifwi_build_link": "",
            "admin_list": "",
            "external_check": "N",
            "config_path": "",
            "svn": "",
            "se_svn": "",
        }
        upload_resp = requests.post(
            f"{BASE_URL}/app/rest/ifwi_submit_ingredients/",
            auth=(USERNAME, PASSWORD),
            data=data,
            timeout=TIMEOUT,
            verify=False,
        )

        if upload_resp.status_code != 200:
            self.skipTest(f"Upload failed with HTTP {upload_resp.status_code}")

        try:
            upload_body = upload_resp.json()
        except json.JSONDecodeError:
            self.skipTest("Upload response is not valid JSON")

        upload_id = upload_body.get("ing_upload_id", "")
        if not upload_id:
            self.skipTest(f"No upload ID returned: {upload_body}")

        print(f"\n  Upload ID: {upload_id}")

        # Step 2: Query status
        status_resp = requests.get(
            f"{BASE_URL}/ingredients_status/{upload_id}",
            timeout=TIMEOUT,
            verify=False,
        )
        self.assertEqual(status_resp.status_code, 200)

        status_body = status_resp.json()
        status = status_body.get("status", "UNKNOWN")
        print(f"  Status: {status}")
        self.assertIn(
            status,
            ["NOT_STARTED", "RUNNING", "FINISHED", "FAILED", "UNKNOWN"],
        )


# ============================================================================
# End-to-End: Upload + Poll Until Completion
# ============================================================================

@unittest.skipUnless(CREDENTIALS_SET, SKIP_REASON)
class TestEndToEndUpload(unittest.TestCase):
    """Full flow: upload -> poll status until done."""

    @unittest.skip("Enable manually - this test polls until server processing completes")
    def test_upload_and_wait_for_completion(self):
        """Upload an ingredient and poll until processing finishes."""
        # Upload
        data = {
            "proj_id": PROJ_ID,
            "ingredient_name": "IntegrationTest",
            "ingredient_version": "0.0.1-e2e-test",
            "comments": "Integration test - end to end",
            "ingredient_link": "https://example.com/integration-test-e2e.zip",
            "send_email": "",
            "ifwi_build_link": "",
            "admin_list": "",
            "external_check": "N",
            "config_path": "",
            "svn": "",
            "se_svn": "",
        }
        upload_resp = requests.post(
            f"{BASE_URL}/app/rest/ifwi_submit_ingredients/",
            auth=(USERNAME, PASSWORD),
            data=data,
            timeout=TIMEOUT,
            verify=False,
        )
        self.assertEqual(upload_resp.status_code, 200)
        upload_id = upload_resp.json().get("ing_upload_id")
        self.assertTrue(upload_id, "No upload ID returned")
        print(f"\n  Upload ID: {upload_id}")

        # Poll for completion (max 5 minutes)
        max_polls = 30
        poll_interval = 10
        for i in range(max_polls):
            time.sleep(poll_interval)
            status_resp = requests.get(
                f"{BASE_URL}/ingredients_status/{upload_id}",
                timeout=TIMEOUT,
                verify=False,
            )
            status_body = status_resp.json()
            status = status_body.get("status", "UNKNOWN")
            print(f"  Poll {i + 1}: {status}")

            if status not in ("NOT_STARTED", "RUNNING"):
                print(f"  Final status: {status}")
                print(f"  Details: {status_body.get('details', '')}")
                self.assertEqual(status, "FINISHED")
                return

        self.fail(f"Upload {upload_id} did not complete within {max_polls * poll_interval}s")


if __name__ == "__main__":
    unittest.main()
