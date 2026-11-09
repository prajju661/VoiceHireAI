"""
Basic tests for the VoiceHire AI backend health and root endpoints.
"""

import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path so 'app' can be imported easily
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.routes import get_health, get_root, router
from app.main import app


class TestBackendHealth(unittest.TestCase):
    """Test suite for backend health check and root endpoints."""

    def test_health_endpoint_payload(self):
        """Test that the /health endpoint handler returns the expected payload."""
        response = get_health()
        self.assertIsInstance(response, dict)
        self.assertEqual(
            response,
            {"status": "healthy", "application": "VoiceHire AI"}
        )

    def test_root_endpoint_payload(self):
        """Test that the root / endpoint handler returns a welcome message."""
        response = get_root()
        self.assertIsInstance(response, dict)
        self.assertIn("message", response)
        self.assertEqual(response["application"], "VoiceHire AI")

    def test_router_routes_registered(self):
        """Test that / and /health routes are defined on the API router."""
        router_paths = [route.path for route in router.routes]
        self.assertIn("/", router_paths)
        self.assertIn("/health", router_paths)

    def test_app_openapi_paths(self):
        """Test that / and /health are exposed in the FastAPI application schema."""
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})
        
        self.assertIn("/", paths, "GET / endpoint must be registered on app")
        self.assertIn("get", paths["/"], "Root endpoint must support GET method")
        
        self.assertIn("/health", paths, "GET /health endpoint must be registered on app")
        self.assertIn("get", paths["/health"], "Health endpoint must support GET method")

    def test_cors_middleware_configured(self):
        """Test that CORS middleware is registered and allows localhost:5173."""
        cors_middlewares = [
            m for m in app.user_middleware
            if m.cls.__name__ == "CORSMiddleware"
        ]
        self.assertTrue(len(cors_middlewares) > 0, "CORSMiddleware should be present")

        allowed_origins = cors_middlewares[0].kwargs.get("allow_origins", [])
        self.assertIn(
            "http://localhost:5173",
            allowed_origins,
            "CORS must allow 'http://localhost:5173'"
        )


if __name__ == "__main__":
    unittest.main()
