import sys
from matrixify_utilities.api.client import ShopifyClient
import requests
import logging
from typing import Optional, Dict, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_test_product(access_token: str, shop_url: str) -> Optional[str]:
    """Fetch first product ID from store"""
    query = """
    {
      products(first: 1) {
        edges {
          node {
            id
            title
            category {
              id
              name
            }
          }
        }
      }
    }
    """
    
    try:
        response = requests.post(
            f"https://{shop_url}/admin/api/2024-04/graphql.json",
            json={'query': query},
            headers={
                'Content-Type': 'application/json',
                'X-Shopify-Access-Token': access_token
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if 'errors' in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            return None
            
        products = data.get('data', {}).get('products', {}).get('edges', [])
        if products and len(products) > 0:
            product = products[0].get('node', {})
            if not product:
                logger.error("No product data found")
                return None
                
            product_id = product.get('id')
            if not product_id:
                logger.error("No product ID found")
                return None
                
            logger.info(f"Found test product: {product.get('title', 'Unknown Title')}")
            
            # Safely get category info
            category = product.get('category', {})
            category_name = category.get('name', 'None') if category else 'None'
            logger.info(f"Current category: {category_name}")
            
            return product_id
            
        logger.error("No products found in store")
        return None
        
    except Exception as e:
        logger.error(f"Failed to fetch test product: {str(e)}")
        return None

def test_category_update(product_id: str, category_id: str, access_token: str, shop_url: str) -> bool:
    """Test updating a product's category using the new taxonomy API"""
    
    mutation = """
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
    """
    
    variables = {
        "input": {
            "id": product_id,
            "category": category_id
        }
    }
    
    logger.info(f"Attempting to update product {product_id} with category {category_id}")
    
    try:
        response = requests.post(
            f"https://{shop_url}/admin/api/2024-04/graphql.json",
            json={
                'query': mutation,
                'variables': variables
            },
            headers={
                'Content-Type': 'application/json',
                'X-Shopify-Access-Token': access_token
            }
        )
        response.raise_for_status()
        data = response.json()
        
        logger.debug(f"Full API response: {data}")
        
        if 'errors' in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            return False
            
        if data.get('data', {}).get('productUpdate', {}).get('userErrors'):
            logger.error(f"User errors: {data['data']['productUpdate']['userErrors']}")
            return False
            
        updated_product = data.get('data', {}).get('productUpdate', {}).get('product', {})
        logger.info(f"Successfully updated product: {updated_product['title']}")
        logger.info(f"New category: {updated_product.get('category', {}).get('name', 'None')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update product category: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_taxonomy_update.py <product_id>")
        sys.exit(1)

    product_id = sys.argv[1]
    client = ShopifyClient()
    success = client.test_taxonomy_update(product_id)
    
    print(f"\nTest {'succeeded' if success else 'failed'}")

if __name__ == "__main__":
    # Test values
    ACCESS_TOKEN = "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"
    SHOP_URL = "color-couturier.myshopify.com"
    CATEGORY_ID = "gid://shopify/TaxonomyCategory/aa"  # Apparel & Accessories
    
    # First get a test product
    product_id = get_test_product(ACCESS_TOKEN, SHOP_URL)
    if product_id:
        logger.info(f"Testing with product ID: {product_id}")
        success = test_category_update(product_id, CATEGORY_ID, ACCESS_TOKEN, SHOP_URL)
        logger.info(f"Test {'succeeded' if success else 'failed'}")
    else:
        logger.error("Could not find a product to test with") 