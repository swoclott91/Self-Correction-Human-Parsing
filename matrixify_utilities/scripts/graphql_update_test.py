import os
import requests
import json
import logging

# Get credentials from environment variables
SHOP = os.getenv("SHOPIFY_SHOP_URL")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

if not SHOP or not TOKEN:
    raise ValueError(
        "Missing required environment variables. Please set:"
        "\n- SHOPIFY_SHOP_URL (e.g., 'your-store.myshopify.com')"
        "\n- SHOPIFY_ACCESS_TOKEN (your admin API access token)"
    )

ENDPOINT = f"https://{SHOP}/admin/api/2024-04/graphql.json"

headers = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}

query = """
mutation updateProductTest($input: ProductInput!, $metafields: [MetafieldsSetInput!]!) {
  productUpdate(input: $input) {
    product {
      id
      title
      category {
        id
        name
        fullName
      }
    }
    userErrors {
      field
      message
    }
  }
  metafieldsSet(metafields: $metafields) {
    metafields {
      id
      namespace
      key
      value
    }
    userErrors {
      field
      message
    }
  }
}
"""

variables = {
    "input": {
        "id": "gid://shopify/Product/14697140683124",
        "category": "gid://shopify/TaxonomyCategory/aa-1-4"
    },
    "metafields": [
        {
            "ownerId": "gid://shopify/Product/14697140683124",
            "namespace": "shopify",
            "key": "age-group",
            "type": "list.metaobject_reference",
            "value": json.dumps(["gid://shopify/Metaobject/215685857652"])
        }
    ]
}

try:
    response = requests.post(ENDPOINT, headers=headers, json={"query": query, "variables": variables})
    response.raise_for_status()  # Raise an error for bad status codes
    result = response.json()
    
    if "errors" in result:
        print("GraphQL Errors:", json.dumps(result["errors"], indent=2))
    else:
        print("Success:", json.dumps(result["data"], indent=2))
        
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
