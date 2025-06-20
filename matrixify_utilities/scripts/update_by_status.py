import os
import sys
import argparse
import logging
from dotenv import load_dotenv
import requests
from .clothing_categorizer import ClothingCategorizer
from .enrich_product_data import ProductEnricher
import json

# Load environment variables
load_dotenv()

# Set API credentials directly
SHOPIFY_API_KEY = "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"
SHOPIFY_SHOP_URL = "color-couturier.myshopify.com"
SHOPIFY_API_URL = f"https://{SHOPIFY_SHOP_URL}/admin/api/2024-01/graphql.json"

HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": SHOPIFY_API_KEY
}

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def fetch_products_by_status(status, limit):
    """Fetch products with given status from Shopify"""
    query = f"""
    {{
      products(first: {limit}, query: "status:{status}") {{
        nodes {{
          id
          title
          descriptionHtml
          status
        }}
      }}
    }}
    """
    
    response = None
    try:
        response = requests.post(SHOPIFY_API_URL, headers=HEADERS, json={"query": query})
        response.raise_for_status()
        return response.json()["data"]["products"]["nodes"]
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        if response:
            logger.error(f"Response: {response.text}")
        raise

def get_metaobject_id(taxonomy_value_gid, attr_key):
    """Look up metaobject ID for a taxonomy value GID"""
    query = '''
        query getMetaobject($handle: String!) {
          metaobjects(first: 1, type: "taxonomy_value", handles: [$handle]) {
            nodes {
              id
            }
          }
        }
    '''
    
    # Convert taxonomy value GID to metaobject handle
    # e.g. gid://shopify/TaxonomyValue/2891 -> shopify--size.10
    value_id = taxonomy_value_gid.split('/')[-1]
    handle = f"shopify--{attr_key}.{value_id}"
    
    response = requests.post(
        SHOPIFY_API_URL,
        headers=HEADERS,
        json={
            "query": query,
            "variables": {"handle": handle}
        }
    )
    
    data = response.json()
    nodes = data.get('data', {}).get('metaobjects', {}).get('nodes', [])
    if nodes:
        return nodes[0]['id']
    return None

def build_metafield_mutation(product_id, attributes):
    """Build metafields mutation with correct types and references"""
    metafields = []
    
    for attr_gid, value_gid in attributes.items():
        if attr_gid == 'category':
            continue
            
        # Convert GIDs to handles
        # e.g. gid://shopify/TaxonomyAttribute/2778 -> size
        attr_key = attr_gid.split('/')[-1]
        
        # Skip certain attributes that should not be set
        if attr_key in ['color']:  # Add other attributes to skip
            continue
            
        # Get metaobject ID for the value
        metaobject_id = get_metaobject_id(value_gid, attr_key)
        if not metaobject_id:
            logger.warning(f"Could not find metaobject for value {value_gid}")
            continue
            
        metafields.append({
            "namespace": "shopify",
            "key": attr_key,
            "type": "list.metaobject_reference",
            "value": json.dumps([metaobject_id]),  # Must be JSON string for list types
            "ownerId": product_id
        })
    
    return metafields

def update_products(status, limit):
    logger.info(f"Fetching up to {limit} products with status: {status}")
    products = fetch_products_by_status(status, limit)
    
    # Initialize ProductEnricher with just confidence threshold
    enricher = ProductEnricher(confidence_threshold=0.5)

    for product in products:
        product_data = {
            'product_id': product['id'],
            'title': product['title'],
            'description': product['descriptionHtml']
        }
        
        successful, failed = enricher.batch_enrich_products([product_data])
        
        if successful:
            payload = successful[0]
            
            # Category update
            category_mutation = {
                "query": '''
                    mutation productUpdate($input: ProductInput!) {
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
                    }
                ''',
                "variables": {
                    "input": {
                        "id": product["id"],
                        "category": payload["category"]
                    }
                }
            }
            
            category_resp = requests.post(SHOPIFY_API_URL, headers=HEADERS, json=category_mutation)
            logger.debug(f"Category update response: {category_resp.json()}")

            # Build metafields with correct references
            # Filter out category and get remaining attributes
            attributes = {k: v for k, v in payload.items() if k != 'category' and k != 'id'}
            metafields = build_metafield_mutation(product["id"], attributes)
            
            if metafields:
                metafields_mutation = {
                    "query": '''
                        mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
                          metafieldsSet(metafields: $metafields) {
                            metafields {
                              id
                              key
                              namespace
                              value
                            }
                            userErrors {
                              field
                              message
                            }
                          }
                        }
                    ''',
                    "variables": {
                        "metafields": metafields
                    }
                }
                
                metafields_resp = requests.post(SHOPIFY_API_URL, headers=HEADERS, json=metafields_mutation)
                logger.debug(f"Metafields update response: {metafields_resp.json()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update Shopify products by status using clothing categorizer.")
    parser.add_argument("--status", type=str, choices=["active", "draft"], required=True, help="Product status to filter by.")
    parser.add_argument("--limit", type=int, default=50, help="Number of products to process.")
    args = parser.parse_args()

    update_products(args.status, args.limit)
