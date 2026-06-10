import os

from cryptography.fernet import Fernet

# Set required env vars before any application module is imported.
# conftest.py at this level runs before pytest collects test files.
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-at-least-32-characters")
os.environ.setdefault("TOTP_ENCRYPTION_KEY", Fernet.generate_key().decode())
