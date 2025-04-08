import logging
from pathlib import Path
import sys
from typing import Dict, Optional
from collections import defaultdict

from api.client import ShopifyClient
from scripts.normalize_categories import CategoryNormalizer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def analyze_product_categories(client: ShopifyClient, normalizer: CategoryNormalizer, 
                             product_id: Optional[str] = None, limit: Optional[int] = None):
    """Analyze product categorization using live Shopify data"""
    category_stats = defaultdict(int)
    changes = []
    unrecognized = []
    
    try:
        # Get products (single or batch)
        if product_id:
            product = client.get_product(product_id)
            if product:
                products = [product]
            else:
                logger.error(f"Product with ID {product_id} not found")
                return None
        else:
            products = []
            for batch in client.get_products_batch(50):  # Process in batches of 50
                products.extend(batch)
                if limit and len(products) >= limit:
                    products = products[:limit]
                    break

        # Process each product
        for product in products:
            title = product.get('title', '')
            description = product.get('description', '')
            current_category = client.get_product_category(product.get('id'))
            
            # Try to normalize category
            normalized_category = normalizer.normalize_category(
                current_category or '',
                title=title,
                description=description
            )
            
            # Track statistics
            if normalized_category:
                category_stats[normalized_category] += 1
                
                if normalized_category != current_category:
                    changes.append({
                        'Handle': product.get('handle'),
                        'Title': title,
                        'Old Category': current_category or 'Not Set',
                        'New Category': normalized_category,
                        'Change Type': 'Update' if current_category else 'New'
                    })
            else:
                unrecognized.append({
                    'Handle': product.get('handle'),
                    'Title': title,
                    'Current Category': current_category
                })
                
        return {
            'category_stats': dict(category_stats),
            'changes': changes,
            'unrecognized': unrecognized
        }
                
    except Exception as e:
        logger.error(f"Error analyzing products: {e}")
        return None

def test_category_normalization(product_id: Optional[str] = None, 
                              limit: Optional[int] = None,
                              debug: bool = False):
    """Test category normalization with live Shopify data"""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    client = ShopifyClient()
    normalizer = CategoryNormalizer()
    
    logger.info("Starting category analysis...")
    
    results = analyze_product_categories(client, normalizer, product_id, limit)
    if not results:
        return False
        
    # Print category changes
    if results['changes']:
        logger.info("\nCategory Changes:")
        for change in results['changes']:
            logger.info(f"\nProduct: {change['Handle']}")
            logger.info(f"Title: {change['Title']}")
            logger.info(f"  Old Category: {change['Old Category']}")
            logger.info(f"  New Category: {change['New Category']}")
            logger.info(f"  Change Type: {change['Change Type']}")
    
    # Print category statistics
    logger.info("\nCategory Statistics:")
    for category, count in results['category_stats'].items():
        logger.info(f"{category}: {count} products")
    
    # Print summary
    total_products = sum(results['category_stats'].values())
    logger.info("\nSummary:")
    logger.info(f"Total products processed: {total_products}")
    logger.info(f"Total changes suggested: {len(results['changes'])}")
    logger.info(f"Total unrecognized: {len(results['unrecognized'])}")
    
    # Calculate recognition rate
    recognition_rate = ((total_products - len(results['unrecognized'])) / total_products * 100) if total_products > 0 else 0
    logger.info(f"Recognition rate: {recognition_rate:.1f}%")
    
    return True

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--product-id", help="Process specific product ID")
    parser.add_argument("--limit", type=int, help="Maximum number of products to process")
    args = parser.parse_args()
    
    success = test_category_normalization(
        product_id=args.product_id,
        limit=args.limit,
        debug=args.debug
    )
    
    if not success:
        sys.exit(1) 