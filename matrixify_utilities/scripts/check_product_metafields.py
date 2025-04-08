import logging
from pathlib import Path
import argparse
import sys
from typing import Optional

# Add parent directory to path so we can import from api
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

from api.client import ShopifyClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_product_details(
    shop_url: Optional[str] = None,
    access_token: Optional[str] = None,
    product_id: Optional[str] = None,
    debug: bool = False
) -> None:
    """Check all relevant details of a product"""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize client
    client = ShopifyClient(shop_url, access_token)
    
    try:
        # Get product
        product = client.get_product(product_id)
        if not product:
            logger.error(f"Product {product_id} not found")
            return
            
        # Print basic product info
        logger.info("\nProduct Details:")
        logger.info(f"ID: {product.get('id')}")
        logger.info(f"Title: {product.get('title')}")
        logger.info(f"Product Type: {product.get('product_type')}")
        
        # Get all metafields
        query = """
        query getProductMetafields($id: ID!) {
            product(id: $id) {
                id
                metafields(first: 50) {
                    nodes {
                        namespace
                        key
                        value
                    }
                }
            }
        }
        """
        
        result = client.graphql_query(query, {'id': f"gid://shopify/Product/{product_id}"})
        
        # Print all metafields
        logger.info("\nMetafields:")
        if result and 'data' in result and 'product' in result['data']:
            metafields = result['data']['product'].get('metafields', {}).get('nodes', [])
            if metafields:
                for metafield in metafields:
                    logger.info(f"Namespace: {metafield['namespace']}")
                    logger.info(f"Key: {metafield['key']}")
                    logger.info(f"Value: {metafield['value']}")
                    logger.info("---")
            else:
                logger.info("No metafields found")
        else:
            logger.error("Failed to fetch metafields")
            
    except Exception as e:
        logger.error(f"Error checking product: {e}")
        if debug:
            import traceback
            logger.debug(traceback.format_exc())

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--shop-url", help="Shopify shop URL")
    parser.add_argument("--access-token", help="Shopify access token")
    parser.add_argument("--product-id", help="Product ID to check")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    check_product_details(
        shop_url=args.shop_url,
        access_token=args.access_token,
        product_id=args.product_id,
        debug=args.debug
    ) 