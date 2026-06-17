import os

from cryptography.fernet import Fernet

# Set required env vars before any application module is imported.
# conftest.py at this level runs before pytest collects test files.
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-at-least-32-characters")
os.environ.setdefault("TOTP_ENCRYPTION_KEY", Fernet.generate_key().decode())
# Disable IP rate limiting in tests: TestClient shares one pseudo-IP, so otherwise
# many auth calls share a window. The limiter algorithm is covered in test_ratelimit.
os.environ.setdefault("RATELIMIT_ENABLED", "false")
