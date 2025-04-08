import logging
from pathlib import Path
import argparse
import sys
from typing import Optional, Dict, List
from tqdm import tqdm

# Add parent directory to path so we can import from api and scripts
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

from api.client import ShopifyClient
from scripts.normalize_categories import CategoryNormalizer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def validate_category_structure(
    shop_url: Optional[str] = None,
    access_token: Optional[str] = None,
    product_id: Optional[str] = None,
    debug: bool = False
) -> bool:
    """Validate the structure of manually set categories"""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize components
    client = ShopifyClient(shop_url, access_token)
    normalizer = CategoryNormalizer()
    
    try:
        # Get product
        product = client.get_product(product_id)
        if not product:
            logger.error(f"Product {product_id} not found")
            return False
            
        # Get current categories
        parent_category = client.get_product_parent_category(product.get('id'))
        child_category = client.get_product_child_category(product.get('id'))
        
        logger.info("\nCurrent Categories:")
        logger.info(f"Parent Category: {parent_category}")
        logger.info(f"Child Category: {child_category}")
        
        # Validate structure
        validation_results = {
            'parent_exists': bool(parent_category),
            'child_exists': bool(child_category),
            'parent_format': False,
            'child_format': False,
            'hierarchy_valid': False
        }
        
        # Check parent category format (should be path-like)
        if parent_category:
            parts = parent_category.split(' > ')
            validation_results['parent_format'] = len(parts) >= 3
            if not validation_results['parent_format']:
                logger.error(f"Parent category should have at least 3 levels: {parent_category}")
        
        # Check child category format (should be single term)
        if child_category:
            validation_results['child_format'] = ' > ' not in child_category
            if not validation_results['child_format']:
                logger.error(f"Child category should be a single term: {child_category}")
        
        # Check hierarchy
        if parent_category and child_category:
            # Child should not be in parent path
            validation_results['hierarchy_valid'] = (
                child_category not in parent_category.split(' > ') and
                normalizer.validate_category_path(f"{parent_category} > {child_category}")
            )
            if not validation_results['hierarchy_valid']:
                logger.error("Invalid category hierarchy")
        
        # Print validation summary
        logger.info("\nValidation Results:")
        for check, result in validation_results.items():
            status = "✓" if result else "✗"
            logger.info(f"{status} {check.replace('_', ' ').title()}")
        
        # Overall validation
        is_valid = all(validation_results.values())
        logger.info(f"\nOverall Structure: {'✓ Valid' if is_valid else '✗ Invalid'}")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Error during validation: {e}")
        if debug:
            import traceback
            logger.debug(traceback.format_exc())
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--shop-url", help="Shopify shop URL")
    parser.add_argument("--access-token", help="Shopify access token")
    parser.add_argument("--product-id", help="Test specific product ID")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    success = validate_category_structure(
        shop_url=args.shop_url,
        access_token=args.access_token,
        product_id=args.product_id,
        debug=args.debug
    )
    
    if not success:
        sys.exit(1) 