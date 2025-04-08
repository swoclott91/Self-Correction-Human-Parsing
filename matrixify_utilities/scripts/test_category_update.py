import logging
from pathlib import Path
import sys
import requests
import json
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from scripts.normalize_categories import CategoryNormalizer
from scripts.taxonomy_mapper import TaxonomyMapper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ShopifyAPI:
    def __init__(self, shop_url: str, access_token: str):
        self.shop_url = shop_url
        self.headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json'
        }
        
    def get_product(self, product_id: int) -> Dict:
        """Fetch product details from Shopify"""
        url = f"{self.shop_url}/admin/api/2024-01/products/{product_id}.json"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()['product']
        
    def update_product_category(self, product_id: int, category_id: str) -> Dict:
        """Update product category using GraphQL"""
        url = f"{self.shop_url}/admin/api/2024-01/graphql.json"
        
        mutation = """
        mutation productUpdate($input: ProductInput!) {
            productUpdate(input: $input) {
                product {
                    id
                    title
                    category {
                        id
                        name
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
                "id": f"gid://shopify/Product/{product_id}",
                "category": category_id
            }
        }
        
        response = requests.post(
            url,
            headers=self.headers,
            json={'query': mutation, 'variables': variables}
        )
        response.raise_for_status()
        return response.json()

def fetch_product_details(product_id: str) -> Optional[dict]:
    """Fetch product details from Shopify"""
    logger.info(f"Fetching product {product_id}...")
    # Mock product for testing
    return {
        'title': 'HYFVE Eyelet Twisted Sweetheart Neck Tube Top',
        'body_html': '',
        'product_type': ''
    }

def main():
    """Main test function"""
    # Test product
    product_id = "14697143894388"
    product = fetch_product_details(product_id)
    
    if not product:
        logger.error("Failed to fetch product")
        return
        
    logger.info(f"Product title: {product['title']}")
    logger.info("")
    logger.info("=== Product Analysis ===")
    logger.info("Analyzing product features and characteristics...")
    logger.info("")
    
    # Initialize normalizer
    normalizer = CategoryNormalizer()
    
    # Test category normalization
    category, confidence, scores = normalizer.normalize_category(
        product['title'],
        description=product['body_html']
    )
    
    # Log results
    logger.info(f"Normalized category: {category}")
    logger.info(f"Confidence: {confidence}")
    logger.info("Detailed scores:")
    for key, value in scores.items():
        logger.info(f"  {key}: {value}")
        
    # Show available categories for debugging
    logger.info("\n=== Available Taxonomy Categories ===")
    logger.info("Relevant category paths:")
    normalizer.taxonomy_mapper.debug_available_categories('top')
    normalizer.taxonomy_mapper.debug_available_categories('blouse')
    
    logger.info("\n=== Final Category Decision ===")
    if category:
        logger.info(f"Selected category: {category}")
        logger.info(f"Confidence: {confidence}")
    else:
        logger.warning("No matching category found")

if __name__ == "__main__":
    main() 