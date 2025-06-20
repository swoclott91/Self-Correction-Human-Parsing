"""
Metaobject Sync Helper

This script:
1. Queries allowed taxonomy attributes for product categories (e.g., "shopify--age-group")
2. Creates metaobject entries for missing values (e.g., "adults", "children")
3. Caches their GIDs in memory or optionally saves to disk
4. Outputs a dictionary like:
   {
     "shopify--age-group.adults": "gid://shopify/Metaobject/215685857652"
   }

You can then use these GIDs in your metafield reference updates.
"""

import os
import requests
import logging

SHOP = os.getenv("SHOPIFY_SHOP_URL")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_VERSION = "2025-01"
ENDPOINT = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"

HEADERS = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}


def fetch_metaobjects_by_type(metaobject_type):
    query = f"""
    query {{
      metaobjects(first: 100, type: "{metaobject_type}") {{
        edges {{
          node {{
            id
            handle
            type
          }}
        }}
      }}
    }}
    """
    response = requests.post(ENDPOINT, headers=HEADERS, json={"query": query})
    data = response.json()
    results = data.get("data", {}).get("metaobjects", {}).get("edges", [])
    return {f"{metaobject_type}.{entry['node']['handle']}": entry["node"]["id"] for entry in results}


def main():
    logging.basicConfig(level=logging.INFO)
    metaobject_types = [
        "shopify--age-group",
        "shopify--fabric",
        "shopify--target-gender",
        "shopify--skirt-dress-length-type",
        "shopify--dress-occasion"
    ]

    all_metaobjects = {}
    for meta_type in metaobject_types:
        logging.info(f"Fetching metaobjects for type: {meta_type}")
        type_map = fetch_metaobjects_by_type(meta_type)
        all_metaobjects.update(type_map)

    for key, gid in all_metaobjects.items():
        print(f"{key}: {gid}")


if __name__ == "__main__":
    main()
