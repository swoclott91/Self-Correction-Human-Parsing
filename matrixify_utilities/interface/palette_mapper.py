import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv("C:/Users/Shane Work/Documents/GitHub/Self-Correction-Human-Parsing/.env")
SHOPIFY_SHOP_URL = os.getenv("SHOPIFY_SHOP_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_API_URL = f"https://{SHOPIFY_SHOP_URL}/admin/api/2025-04/graphql.json"

PALETTE_METAOBJECTS = {
    "Clear Spring": "gid://shopify/Metaobject/221436641652",
    "Clear Winter": "gid://shopify/Metaobject/221436707188",
    "Cool Winter": "gid://shopify/Metaobject/221436739956",
    "Deep Winter": "gid://shopify/Metaobject/221436805492",
    "Warm Autumn": "gid://shopify/Metaobject/221436838260",
    "Warm Spring": "gid://shopify/Metaobject/221436903796",
    "Cool Summer": "gid://shopify/Metaobject/221436936564",
    "Deep Autumn": "gid://shopify/Metaobject/221436969332",
    "Soft Autumn": "gid://shopify/Metaobject/221437002100",
    "Soft Summer": "gid://shopify/Metaobject/221437034868",
    "Light Summer": "gid://shopify/Metaobject/221437067636",
    "Light Spring": "gid://shopify/Metaobject/221437526388",
    # Populate all 12 seasonal palettes
}

def assign_palette_metafield_to_variant(variant_id: str, palette_name: str) -> dict:
    """
    Assigns a seasonal palette to the given variant via `custom.palette` metafield.
    """
    if palette_name not in PALETTE_METAOBJECTS:
        raise ValueError(f"Unknown palette: {palette_name}")

    metafield_payload = {
        "query": """
        mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
          metafieldsSet(metafields: $metafields) {
            metafields { id key value }
            userErrors { field message }
          }
        }
        """,
        "variables": {
            "metafields": [
                {
                    "ownerId": variant_id,
                    "namespace": "custom",
                    "key": "palette",
                    "type": "metaobject_reference",
                    "value": PALETTE_METAOBJECTS[palette_name],
                }
            ]
        }
    }

    response = requests.post(SHOPIFY_API_URL, headers={
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN
    }, json=metafield_payload)

    return response.json()
