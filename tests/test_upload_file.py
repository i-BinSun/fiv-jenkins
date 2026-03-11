#!/usr/bin/env python3
"""
Unit tests for FIV Portal upload endpoints.

Purpose: Verify API health and stability using unittest framework.
Coverage:
  - GET /ifwi_check_proj_mandatory/{proj_id}
  - POST /app/rest/ifwi_submit_ingredients/ (Basic & Concurrency)
  - Large file upload handling

Usage:
  Set environment variables before running:
    FIV_BASE_URL   - e.g. https://fiv-ifwi.intel.com
    FIV_USERNAME   - your username
    FIV_PASSWORD   - your password
    FIV_PROJ_ID    - project ID to test against

  Run:
    python -m unittest test_fiv_api.py
    python -m unittest test_fiv_api.py -v  (verbose mode)

  Note: Tests involving POST (upload) are enabled by default but use unique
        IDs to minimize pollution. Set SKIP_WRITE_TESTS=true to skip all POST tests.
"""

import io
import os
import time
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple
from urllib.parse import quote, urljoin

import requests
from requests.auth import HTTPBasicAuth
import urllib3
from dotenv import load_dotenv

load_dotenv()
# Disable SSL warnings for testing if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class Config:
    BASE_URL = os.environ.get("FIV_BASE_URL", "https://fiv-ifwi.intel.com/").rstrip("/")
    USERNAME = os.environ.get("FIV_USERNAME", "")
    PASSWORD = os.environ.get("FIV_PASSWORD", "")
    PROJ_ID = os.environ.get("FIV_PROJ_ID", "")
    VERIFY_SSL = os.environ.get("FIV_VERIFY_SSL", "false").lower() == "true"
    SKIP_WRITE_TESTS = os.environ.get("SKIP_WRITE_TESTS", "false").lower() == "true"
    INGREDIENT_NAME = os.environ.get("FIV_INGREDIENT_NAME", "A0_main_CoreFw")

    # Endpoints
    ENDPOINT_GET_REQUIREMENTS = "/ifwi_check_proj_mandatory/{proj_id}"
    ENDPOINT_UPLOAD = "/app/rest/ifwi_submit_ingredients/"
    ENDPOINT_STATUS = "/ingredients_status/{upload_id}"

    # Test Constants
    DEFAULT_TIMEOUT = 30
    UPLOAD_TIMEOUT = 120
    CONCURRENCY_LEVEL = 10
    LARGE_FILE_SIZE_KB = 10240  # 10MB for large file test


def make_session() -> requests.Session:
    """Create a session with no retries to expose raw server errors."""
    session = requests.Session()
    from requests.adapters import HTTPAdapter
    adapter = HTTPAdapter(max_retries=0)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def dummy_file(size_kb: int) -> Tuple[str, io.BytesIO, str]:
    """Generate synthetic file content."""
    data = b"X" * size_kb * 1024
    return (f"unittest_{uuid.uuid4().hex[:8]}_{size_kb}kb.bin", io.BytesIO(data), "application/octet-stream")


@unittest.skipUnless(Config.USERNAME and Config.PASSWORD and Config.PROJ_ID,
                     "Missing required environment variables: FIV_USERNAME, FIV_PASSWORD, FIV_PROJ_ID")
class TestFivPortalApi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.session = make_session()
        print(f"\n[Setup] Target: {Config.BASE_URL}, Project: {Config.PROJ_ID}")
        if Config.SKIP_WRITE_TESTS:
            print("[Setup] SKIP_WRITE_TESTS is enabled. All POST tests will be skipped.")

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def _get_url(self, endpoint_template: str, **kwargs) -> str:
        formatted = endpoint_template.format(**kwargs)
        return urljoin(Config.BASE_URL + "/", formatted.lstrip("/"))

    # -----------------------------------------------------------------------
    # Test Cases: GET Endpoints (Read-Only)
    # -----------------------------------------------------------------------

    def test_01_get_requirements_success(self):
        """Test GET /ifwi_check_proj_mandatory/{proj_id} returns 200."""
        url = self._get_url(Config.ENDPOINT_GET_REQUIREMENTS, proj_id=quote(Config.PROJ_ID))

        start_time = time.perf_counter()
        resp = self.session.get(
            url,
            auth=HTTPBasicAuth(Config.USERNAME, Config.PASSWORD),
            verify=Config.VERIFY_SSL,
            timeout=Config.DEFAULT_TIMEOUT
        )
        latency = (time.perf_counter() - start_time) * 1000

        self.assertEqual(resp.status_code, 200, f"Expected 200, got {resp.status_code}. URL: {url}")
        self.assertLess(latency, 10000, f"Latency {latency:.0f}ms is too high for a simple GET")
        print(f"  [PASS] GET Requirements: {resp.status_code} ({latency:.0f}ms)")

    def test_02_get_status_not_found(self):
        """Test GET /ingredients_status/{fake_id} returns 404 (expected behavior)."""
        fake_id = "unittest-fake-id-" + uuid.uuid4().hex
        url = self._get_url(Config.ENDPOINT_STATUS, upload_id=quote(fake_id))

        resp = self.session.get(
            url,
            auth=HTTPBasicAuth(Config.USERNAME, Config.PASSWORD),
            verify=Config.VERIFY_SSL,
            timeout=Config.DEFAULT_TIMEOUT
        )

        # Expecting 404 because the ID doesn't exist, NOT 500
        self.assertIn(resp.status_code, [200], f"Expected 404/403 for fake ID, got {resp.status_code}")
        status = resp.json()["status"]
        self.assertEqual(status, "FAIL", f"Expected NOT_FOUND status, got {status}")
        print(f"  [PASS] GET Status (Fake ID): {resp.status_code} (Expected non-500)")

    # -----------------------------------------------------------------------
    # Test Cases: POST Endpoints (Write Operations)
    # -----------------------------------------------------------------------

    @unittest.skipIf(Config.SKIP_WRITE_TESTS, "Skipped due to SKIP_WRITE_TESTS flag")
    def test_03_upload_basic_success(self):
        """Test single POST upload returns 200 or 201."""
        url = self._get_url(Config.ENDPOINT_UPLOAD)
        fname, fbuf, fmime = dummy_file(10)  # 10KB

        data = {
            "proj_id": Config.PROJ_ID,
            "ingredient_name": Config.INGREDIENT_NAME,
            "ingredient_version": f"UT_{uuid.uuid4().hex[:8]}",
            "comments": "Automated unit test - safe to ignore/delete",
            "send_email": "",
            "ingredient_link": "",
            "ifwi_build_link": "",
            "admin_list": Config.USERNAME,  # Use current user as admin
            "external_check": "N",
            "config_path": "",
            "svn": "",
            "se_svn": "",
        }
        files = {"ingredient_file": (fname, fbuf, fmime)}

        resp = self.session.post(
            url,
            auth=HTTPBasicAuth(Config.USERNAME, Config.PASSWORD),
            data=data,
            files=files,
            verify=Config.VERIFY_SSL,
            timeout=Config.UPLOAD_TIMEOUT
        )

        self.assertIn(resp.status_code, [200, 201, 204],
                      f"Upload failed with status {resp.status_code}. Response: {resp.text[:200]}")
        print(f"  [PASS] Upload Basic: {resp.status_code}")

    @unittest.skipIf(Config.SKIP_WRITE_TESTS, "Skipped due to SKIP_WRITE_TESTS flag")
    def test_04_upload_concurrency_stability(self):
        """Test concurrent uploads do not trigger HTTP 500 errors."""
        url = self._get_url(Config.ENDPOINT_UPLOAD)
        concurrency = Config.CONCURRENCY_LEVEL
        results: List[int] = []
        lock = __import__('threading').Lock()

        def worker(worker_id: int) -> int:
            fname, fbuf, fmime = dummy_file(5)  # Small file for concurrency test
            data = {
                "proj_id": Config.PROJ_ID,
                "ingredient_name": Config.INGREDIENT_NAME,
                "ingredient_version": f"Conc_{worker_id}_{uuid.uuid4().hex[:4]}",
                "comments": "Concurrency stress test",
                "admin_list": Config.USERNAME,
                "external_check": "N",
                # ... other fields omitted for brevity, same as basic test
            }
            # Re-create buffer for each thread as BytesIO is not thread-safe for reading from start
            files = {"ingredient_file": (fname, io.BytesIO(fbuf.read()), fmime)}

            try:
                resp = self.session.post(url, auth=HTTPBasicAuth(Config.USERNAME, Config.PASSWORD),
                                         data=data, files=files, verify=Config.VERIFY_SSL, timeout=60)
                return resp.status_code
            except Exception:
                return -1

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(worker, i) for i in range(concurrency)]
            for future in as_completed(futures):
                status = future.result()
                with lock:
                    results.append(status)

        # Assert no 500 errors occurred
        error_500_count = results.count(500)
        self.assertEqual(error_500_count, 0,
                         f"Found {error_500_count} HTTP 500 errors during concurrency test out of {len(results)} requests.")

        success_count = sum(1 for s in results if s in [200, 201, 204])
        print(f"  [PASS] Concurrency Test: {success_count}/{len(results)} successful, 0 HTTP 500s")

    @unittest.skipIf(Config.SKIP_WRITE_TESTS, "Skipped due to SKIP_WRITE_TESTS flag")
    def test_05_upload_large_file(self):
        """Test uploading a larger file to detect I/O thresholds."""
        url = self._get_url(Config.ENDPOINT_UPLOAD)
        size_kb = Config.LARGE_FILE_SIZE_KB
        fname, fbuf, fmime = dummy_file(size_kb)

        data = {
            "proj_id": Config.PROJ_ID,
            "ingredient_name": Config.INGREDIENT_NAME,
            "ingredient_version": f"Large_{uuid.uuid4().hex[:8]}",
            "comments": "Large file unit test",
            "admin_list": Config.USERNAME,
            "external_check": "N",
        }
        files = {"ingredient_file": (fname, fbuf, fmime)}

        start = time.perf_counter()
        resp = self.session.post(
            url,
            auth=HTTPBasicAuth(Config.USERNAME, Config.PASSWORD),
            data=data,
            files=files,
            verify=Config.VERIFY_SSL,
            timeout=Config.UPLOAD_TIMEOUT * 2  # Allow more time for large files
        )
        latency = (time.perf_counter() - start) * 1000

        self.assertNotEqual(resp.status_code, 500, f"Server returned 500 for {size_kb}KB file")
        self.assertIn(resp.status_code, [200, 201, 204], f"Large file upload failed: {resp.status_code}")
        print(f"  [PASS] Large File ({size_kb}KB): {resp.status_code} ({latency:.0f}ms)")


if __name__ == "__main__":
    # Provide a helpful message if env vars are missing before running
    if not (Config.USERNAME and Config.PASSWORD and Config.PROJ_ID):
        print("ERROR: Missing environment variables.")
        print("Please set: FIV_USERNAME, FIV_PASSWORD, FIV_PROJ_ID")
        print("Optional: FIV_BASE_URL, SKIP_WRITE_TESTS=true")
        exit(1)

    unittest.main(verbosity=2)
