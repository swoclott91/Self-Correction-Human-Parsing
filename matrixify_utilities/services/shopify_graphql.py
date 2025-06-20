import requests
from matrixify_utilities.config.settings import GRAPHQL_URL, ACCESS_TOKEN
from typing import List, Optional
import datetime

def fetch_products(status: Optional[str] = "ACTIVE", created_since_days: Optional[int] = None, page_size: int = 50):
    cursor = None
    products = []
    has_next_page = True

    filters = []
    if status:
        filters.append(f"status:{status}")
    if created_since_days:
        since = (datetime.datetime.utcnow() - datetime.timedelta(days=created_since_days)).isoformat() + "Z"
        filters.append(f"created_at:>={since}")
    query_filter = " ".join(filters)

    while has_next_page:
        after_cursor = f', after: "{cursor}"' if cursor else ''
        query = f"""
        query {{
          products(first: {page_size}{after_cursor}, query: "{query_filter}") {{
            pageInfo {{
              hasNextPage
              endCursor
            }}
            nodes {{
              id
              title
              handle
              variants(first: 100) {{
                edges {{
                  node {{
                    id
                    price
                  }}
                }}
              }}
            }}
          }}
        }}
        """

        headers = {
            "X-Shopify-Access-Token": ACCESS_TOKEN,
            "Content-Type": "application/json"
        }

        response = requests.post(GRAPHQL_URL, json={"query": query}, headers=headers)
        data = response.json()

        # Handle error response gracefully
        if "errors" in data:
            print("❌ GraphQL error returned:", data["errors"])
            return []

        try:
            nodes = data["data"]["products"]["nodes"]
            print(f"[fetch_products] Retrieved {len(nodes)} products from this page")
        except KeyError:
            print("❌ Unexpected response structure:", data)
            return []

        products.extend(nodes)
        has_next_page = data["data"]["products"]["pageInfo"]["hasNextPage"]
        cursor = data["data"]["products"]["pageInfo"]["endCursor"]

    return products

def update_product_metafields(metafields):
    """
    Update product metafields using the Shopify Admin API.
    
    Args:
        metafields (list): List of metafield objects to update
        
    Returns:
        dict: Response from the API containing updated metafields or errors
    """
    mutation = """
    mutation MetafieldsSet($metafields: [MetafieldsSetInput!]!) {
        metafieldsSet(metafields: $metafields) {
            metafields {
                id
                namespace
                key
                value
                type
                ownerType
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    variables = {
        "metafields": metafields
    }
    
    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=headers)
    data = response.json()

    # Handle error response gracefully
    if "errors" in data:
        print("❌ GraphQL error returned:", data["errors"])
        return {}

    return data.get("data", {}).get("metafieldsSet", {})
