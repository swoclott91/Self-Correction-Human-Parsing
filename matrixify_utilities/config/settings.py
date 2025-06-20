import os
from dotenv import load_dotenv
from pathlib import Path

# Construct absolute path to the .env file at project root
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

# Load Shopify credentials from .env
SHOP_URL = os.getenv("SHOPIFY_SHOP_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
GRAPHQL_URL = f"https://{SHOP_URL}/admin/api/2025-04/graphql.json"
print("[settings.py] SHOP_URL:", SHOP_URL)
print("[settings.py] ACCESS_TOKEN found:", bool(ACCESS_TOKEN))