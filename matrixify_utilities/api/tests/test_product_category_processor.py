import logging
from typing import Dict, Optional
import argparse

# Use relative imports from current package location
from ...scripts.normalize_categories import CategoryMatcher
from ..shopify_graphql_client import ShopifyGraphQLClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_product_categorization(product_id: str, debug: bool = False):
    """Test category normalization for a specific product using GraphQL API"""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Initialize GraphQL client and category matcher
    client = ShopifyGraphQLClient()
    matcher = CategoryMatcher()
    
    # Query product data
    query = """
    query getProduct($id: ID!) {
        product(id: $id) {
            id
            title
            description
            productType
            vendor
            tags
        }
    }
    """
    
    try:
        # Get product data
        result = client.execute(query, variables={'id': f"gid://shopify/Product/{product_id}"})
        product = result.get('data', {}).get('product')
        
        if not product:
            logger.error(f"Product {product_id} not found")
            return False
            
        # Get current category info
        current_category = product.get('productType', '')
        
        logger.info(f"\nAnalyzing Product: {product['title']}")
        logger.info(f"Current Category: {current_category}")
        
        # Get category scores
        scores = {}
        combined_text = f"{product['title']} {product.get('description', '')}"
        
        for category, patterns in matcher.category_indicators.items():
            score = matcher.score_category_match(
                combined_text,
                patterns,
                product.get('vendor')
            )
            if score > 0:
                scores[category] = score
        
        # Sort and display top matches
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_scores:
            logger.info("\nTop Category Matches:")
            for category, score in sorted_scores[:3]:
                logger.info(f"\nCategory: {category}")
                logger.info(f"Score: {score:.2f}")
                
                # Show matching patterns
                patterns = matcher.category_indicators[category]
                logger.info("\nMatching Patterns:")
                logger.info(f"Required: {[p for p in patterns['required'] if p.lower() in product['title'].lower()]}")
                logger.info(f"Optional: {[p for p in patterns['optional'] if p.lower() in product['title'].lower()]}")
        else:
            logger.info("\nNo category matches found")
            
        return True
            
    except Exception as e:
        logger.error(f"Error processing product: {e}")
        if debug:
            import traceback
            logger.debug(traceback.format_exc())
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-id", required=True, help="Shopify product ID to analyze")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    success = test_product_categorization(args.product_id, args.debug)
    if not success:
        import sys
        sys.exit(1) 