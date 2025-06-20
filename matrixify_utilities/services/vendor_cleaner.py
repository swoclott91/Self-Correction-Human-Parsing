from typing import Tuple, List, Optional
import requests
import re
from matrixify_utilities.config.settings import GRAPHQL_URL, ACCESS_TOKEN
from datetime import datetime

VENDOR_PREFIXES = ["MABLE", "ADORA", "ZENANA", "KANCAN", "Mittoshop", "RISEN", "SAGE + FIG", "She + Sky", "Aemi+Co", "Aemi + Co", "American Bazi", "And The Why", "Annie Wear", "Basic Bae", "BiBi", "BOMBOM", "Celeste", "Cesfemme", "Davi & Dani", "Double Take", "GeeGee", "Heimish", "HYFVE", "Judy Blue", "MONO B", "Nicole Lee USA", "POL", "SAGE+FIG", "SO ME", "SYNZ", "Umgee USA", "Umgee", "VERY J"]

def get_first_color_option(product_gid: str) -> Optional[str]:
    query = """
    query GetProductVariantOptions($id: ID!) {
      product(id: $id) {
        variants(first: 1) {
          edges {
            node {
              selectedOptions {
                name
                value
              }
            }
          }
        }
      }
    }
    """
    
    variables = {
        "id": product_gid
    }

    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=headers)
    result = response.json()

    try:
        variant = result['data']['product']['variants']['edges'][0]['node']
        for option in variant['selectedOptions']:
            if option['name'].lower() == 'color':
                return option['value']
    except (KeyError, IndexError) as e:
        print(f"Error getting color option: {e}")
        print(f"API Response: {result}")
        return None

    return None

def clean_title_and_handle(title: str) -> Tuple[str, str]:
    for prefix in VENDOR_PREFIXES:
        pattern = re.compile(rf"^{re.escape(prefix)}[\s:\-–—]+", re.IGNORECASE)
        if pattern.match(title):
            new_title = pattern.sub("", title).strip()
            new_handle = re.sub(r"[^a-z0-9]+", "-", new_title.lower()).strip("-")
            return new_title, new_handle
    return title, re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

def update_product(product_gid: str, new_title: str, new_handle: str):
    # First attempt with original handle
    result = _try_update_product(product_gid, new_title, new_handle)
    
    # If there's a handle conflict, try with color-based handle
    if has_handle_error(result):
        print(f"Handle conflict for {new_handle}, trying to get color option...")
        color = get_first_color_option(product_gid)
        print(f"Got color option: {color}")
        
        if color:
            color_slug = re.sub(r"[^a-z0-9]+", "-", color.lower()).strip("-")
            new_handle_with_color = f"{new_handle}-{color_slug}"
            print(f"Trying color-based handle: {new_handle_with_color}")
            result = _try_update_product(product_gid, new_title, new_handle_with_color)
            
            # If color-based handle also fails, keep original title but use vendor-based handle
            if has_handle_error(result):
                print("Color-based handle also failed, using vendor-based handle...")
                vendor_handle = re.sub(r"[^a-z0-9]+", "-", result['data']['productUpdate']['product']['title'].lower()).strip("-")
                print(f"Trying vendor-based handle: {vendor_handle}")
                result = _try_update_product(product_gid, result['data']['productUpdate']['product']['title'], vendor_handle)
        else:
            print("No color option found, using vendor-based handle...")
            vendor_handle = re.sub(r"[^a-z0-9]+", "-", result['data']['productUpdate']['product']['title'].lower()).strip("-")
            print(f"Trying vendor-based handle: {vendor_handle}")
            result = _try_update_product(product_gid, result['data']['productUpdate']['product']['title'], vendor_handle)
    
    return result

def _try_update_product(product_gid: str, new_title: str, new_handle: str):
    query = """
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product {
          id
          title
          handle
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
            "id": product_gid,
            "title": new_title,
            "handle": new_handle
        }
    }

    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=headers)
    return response.json()

def has_handle_error(result):
    """Check if the result contains a handle conflict error."""
    if 'data' in result and 'productUpdate' in result['data']:
        user_errors = result['data']['productUpdate'].get('userErrors', [])
        for error in user_errors:
            if 'handle' in error.get('field', []) and 'already in use' in error.get('message', ''):
                return True
    return False
