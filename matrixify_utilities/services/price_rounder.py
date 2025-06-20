from typing import List
import math
import requests
from matrixify_utilities.config.settings import GRAPHQL_URL, ACCESS_TOKEN

def round_up_price(price: str) -> str:
    return str(math.ceil(float(price)))

def update_product_variant_prices(product_id: str, variant_updates: List[dict]) -> dict:
    """Bulk update variant prices for a product using the Shopify Admin GraphQL API."""
    query = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        product {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {
        "productId": product_id,
        "variants": variant_updates
    }

    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers=headers
    )
    
    data = response.json()
    
    if "errors" in data:
        print("❌ GraphQL error:", data["errors"])
        return {}
        
    return data.get("data", {}).get("productVariantsBulkUpdate", {})
