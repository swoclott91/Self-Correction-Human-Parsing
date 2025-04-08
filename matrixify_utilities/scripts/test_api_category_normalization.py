import logging
from pathlib import Path
import argparse
import sys
from typing import Optional, Dict, List
from tqdm import tqdm

# Configure logging before imports
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger(__name__)

# Set debug logging for taxonomy mapper
taxonomy_logger = logging.getLogger('matrixify_utilities.utils.taxonomy_mapper')
taxonomy_logger.setLevel(logging.DEBUG)

from matrixify_utilities.api.client import ShopifyClient
from matrixify_utilities.utils.taxonomy_mapper import TaxonomyMapper
from matrixify_utilities.scripts.normalize_categories import CategoryNormalizer
# TODO: Import API-related modules once they're ready
# from matrixify_utilities.api.product_category_processor import ProductCategoryProcessor

def test_category_normalization(
    product_id: str,
    debug: bool = False,
    live: bool = False
) -> bool:
    """Test category normalization with live product data"""
    if debug:
        logger.setLevel(logging.DEBUG)
        # Also set debug for taxonomy mapper
        taxonomy_logger.setLevel(logging.DEBUG)
        
    client = ShopifyClient()
    normalizer = CategoryNormalizer()
    
    try:
        # Get product details
        product = client.get_product(product_id)
        if not product:
            logger.error(f"Could not find product {product_id}")
            return False
            
        # Get normalized category
        category, confidence, scores = normalizer.normalize_category(
            product.get('title', ''),
            product.get('description', '')
        )
        
        if debug:
            print(f"\nProduct: {product.get('title')}")
            print(f"Raw Category: {scores['raw_category']}")
            print(f"Standard Category: {scores['standard_category']}")
            print(f"Taxonomy ID: {scores['taxonomy_id']}")
            print(f"Confidence: {confidence}")
            print(f"Score Breakdown: {scores}")
                
        if confidence > 0.7 and scores['taxonomy_id']:
            if live:
                success = client.update_product_taxonomy(
                    product_id,
                    scores['taxonomy_id']
                )
                if success:
                    logger.info(f"Updated taxonomy for {product.get('title')}")
            else:
                logger.info("Dry run - would update taxonomy")
                
        return True
        
    except Exception as e:
        logger.error(f"Error processing product: {e}", exc_info=True)
        return False

def main():
    parser = argparse.ArgumentParser(description='Test category normalization')
    parser.add_argument('--product-id', required=True, help='Product ID to test')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--live', action='store_true', help='Use live API')
    
    args = parser.parse_args()
    
    try:
        test_category_normalization(args.product_id, args.debug, args.live)
    except Exception as e:
        logger.error(f"Error testing category normalization: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 