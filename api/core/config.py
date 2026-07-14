"""
Configuration module for the API.

This module loads environment variables and sets up configuration constants
for the application, such as API host and port.
"""

import os

from dotenv import load_dotenv

load_dotenv()

API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8080"))
