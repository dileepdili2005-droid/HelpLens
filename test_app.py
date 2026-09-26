import unittest
import json
import io
import os
from PIL import Image

from app import app
from config import Config
import database
import ai_service
import ocr_service

class HelpLensTestSuite(unittest.TestCase):
    """Automated test suite verifying HelpLens core functionality and API contracts."""

    def setUp(self):
        """Prepare test client and test database."""
        app.config["TESTING"] = True
        self.client = app.test_client()
        database.init_db()

    def test_01_health_check(self):
        """Verify the health check endpoint returns 200 and valid JSON status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("app_name"), "HelpLens")
        self.assertIn("active_model", data)

    def test_02_index_page(self):
        """Verify the main single-page dashboard renders with 200 OK."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"HelpLens", response.data)
        self.assertIn(b"Solver Studio", response.data)

    def test_03_analyze_empty_request_rejected(self):
        """Verify that sending an empty request returns 400 Bad Request."""
        response = self.client.post("/api/analyze", data={})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data.get("success"))

    def test_04_analyze_text_problem(self):
        """Verify text-based problem diagnosis returns valid structured guidance."""
        payload = {
            "problem_text": "My Bosch washing machine shows error code E18 and water will not drain.",
            "category": "Appliance & Codes",
            "urgency": "Beginner / Low Tools"
        }
        response = self.client.post("/api/analyze", data=payload)
        self.assertEqual(response.status_code, 200)
        res_json = response.get_json()
        self.assertTrue(res_json.get("success"))
        
        # Verify schema structure
        data = res_json.get("data", {})
        self.assertIn("problem_title", data)
        self.assertIn("safety_warnings", data)
        self.assertIn("steps", data)
        self.assertIn("tools_needed", data)
        self.assertIn("diagnosis", data)
        self.assertIn("when_to_call_pro", data)
        self.assertGreater(len(data.get("steps", [])), 0)

    def test_05_analyze_with_image_upload(self):
        """Verify image upload pipeline, preprocessing, and response."""
        # Create an in-memory test image
        img = Image.new("RGB", (200, 200), color=(73, 109, 137))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        data = {
            "problem_text": "Examine this appliance panel for error markers.",
            "category": "Home & DIY",
            "image": (img_bytes, "test_appliance.jpg")
        }
        response = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        res_json = response.get_json()
        self.assertTrue(res_json.get("success"))
        self.assertIsNotNone(res_json.get("image_url"))

    def test_06_database_history_and_bookmarks(self):
        """Verify database query retrieval, bookmark toggling, and feedback submission."""
        # Retrieve history
        resp = self.client.get("/api/history")
        self.assertEqual(resp.status_code, 200)
        history_data = resp.get_json()
        self.assertTrue(history_data.get("success"))
        items = history_data.get("items", [])
        self.assertGreater(len(items), 0)

        # Test bookmark toggle on the most recent item
        first_id = items[0]["id"]
        bm_resp = self.client.post(f"/api/history/{first_id}/bookmark")
        self.assertEqual(bm_resp.status_code, 200)
        bm_data = bm_resp.get_json()
        self.assertTrue(bm_data.get("success"))
        self.assertTrue(bm_data.get("bookmarked"))

        # Test feedback submission
        fb_resp = self.client.post(
            f"/api/history/{first_id}/feedback",
            json={"rating": 1, "note": "Clear instructions, fixed my washer!"}
        )
        self.assertEqual(fb_resp.status_code, 200)
        self.assertTrue(fb_resp.get_json().get("success"))

    def test_07_mock_engine_presets(self):
        """Verify all mock engine presets return consistent structured schema."""
        test_prompts = [
            ("kitchen faucet leak", "Plumbing & Water"),
            ("wifi router red light", "Electronics & Tech"),
            ("yellowing houseplant leaves", "Garden & Plants"),
            ("car check engine light", "Automotive"),
            ("care label symbols on shirt", "Clothing & Labels")
        ]
        for prompt, cat in test_prompts:
            result = ai_service.generate_mock_guidance(prompt, category=cat)
            self.assertIn("problem_title", result)
            self.assertIn("safety_warnings", result)
            self.assertIn("steps", result)
            self.assertIn("tools_needed", result)
            self.assertIsInstance(result["steps"], list)
            self.assertGreaterEqual(len(result["steps"]), 3)

if __name__ == "__main__":
    unittest.main()
