import logging
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from api.client import ShopifyClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_variant_connections(example_product_id: str):
    """Test connecting variant options to metafield definitions"""
    client = ShopifyClient()
    
    # 1. Inspect example product
    product = client.inspect_product_metafields(example_product_id)
    if not product:
        logger.error("Failed to get example product")
        return False
        
    # 2. Get metafield definitions
    definitions = client.get_metafield_definitions(namespace="shopify")
    if not definitions:
        logger.error("Failed to get metafield definitions")
        return False
        
    # Log what we found
    logger.info("\nProduct Structure:")
    logger.info(f"Title: {product['title']}")
    logger.info("\nVariants:")
    for variant in product['variants']['nodes']:
        logger.info(f"\n  Variant: {variant['title']}")
        logger.info("  Options:")
        for option in variant['selectedOptions']:
            logger.info(f"    {option['name']}: {option['value']}")
        logger.info("  Metafields:")
        for metafield in variant['metafields']['nodes']:
            logger.info(f"    {metafield['namespace']}.{metafield['key']}: {metafield['value']}")
            
    logger.info("\nAvailable Definitions:")
    for definition in definitions:
        logger.info(f"  {definition['namespace']}.{definition['key']}: {definition['id']}")
        
    return True

def test_color_connection(product_id: str, color_metaobject_id: str):
    """Test connecting a product and its variants to a color metaobject"""
    client = ShopifyClient()
    
    # 1. Get product details
    product = client.inspect_product_metafields(product_id)
    if not product:
        logger.error("Failed to get product")
        return False
    
    # 2. Connect product to color
    if not client.connect_product_color(product_id, color_metaobject_id):
        logger.error("Failed to connect product color")
        return False
    
    # 3. Connect each variant to color
    for variant in product['variants']['nodes']:
        # Only connect variants with matching color
        color_option = next((opt for opt in variant['selectedOptions'] 
                           if opt['name'].lower() == 'color'), None)
        if color_option:
            if not client.connect_variant_color(variant['id'], color_metaobject_id):
                logger.error(f"Failed to connect variant {variant['id']}")
                return False
            
    return True

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--product-id', required=True,
                       help='ID of product to connect')
    parser.add_argument('--color-id', required=True,
                       help='ID of color metaobject to connect')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    success = test_color_connection(args.product_id, args.color_id)
    if not success:
        sys.exit(1) 