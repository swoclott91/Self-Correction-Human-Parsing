import logging
from pathlib import Path
import sys
import argparse
from tqdm import tqdm
from typing import Optional

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from api.client import ShopifyClient
from api.product_color_processor import ProductColorProcessor
from api.metaobject_registry import MetaobjectRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_product_color_processing(
    shop_url: str = "color-couturier.myshopify.com",
    access_token: str = None,
    dry_run: bool = True,
    product_id: Optional[str] = None,
    limit: Optional[int] = None,
    debug: bool = False
) -> bool:
    """Test the product color processing pipeline"""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logger.info("Starting product processing")
    if dry_run:
        logger.info("DRY RUN")
    
    client = ShopifyClient(shop_url, access_token)
    processor = ProductColorProcessor(client)
    
    try:
        processed, colors, connections = processor.process_all_products(
            dry_run=dry_run,
            product_id=product_id,
            limit=limit
        )
        return True
    except Exception as e:
        logger.error(f"Error in test: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--product-id", help="Process specific product ID")
    parser.add_argument("--limit", type=int, help="Maximum number of products to process")
    args = parser.parse_args()
    
    success = test_product_color_processing(
        debug=args.debug,
        product_id=args.product_id,
        limit=args.limit
    )
    
    if not success:
        sys.exit(1) 