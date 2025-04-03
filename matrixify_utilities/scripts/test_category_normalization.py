import pandas as pd
from normalize_categories import process_csv
import logging
from pathlib import Path
from collections import defaultdict
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def analyze_product_names(df, unrecognized_categories):
    """Analyze product names for common patterns in unrecognized categories"""
    product_patterns = defaultdict(list)
    
    # Common clothing keywords to look for
    clothing_keywords = {
        'top': ['blouse', 'shirt', 'tank', 'tee', 'tunic', 'crop'],
        'dress': ['dress', 'gown', 'maxi', 'midi', 'mini'],
        'bottom': ['pant', 'jean', 'short', 'skirt', 'legging'],
        'outerwear': ['jacket', 'coat', 'cardigan', 'blazer', 'sweater'],
        'set': ['set', 'outfit', 'coordinate', 'suit', 'ensemble'],
        'one-piece': ['jumpsuit', 'romper', 'playsuit', 'overall'],
    }
    
    # Analyze each unrecognized category
    for category in unrecognized_categories:
        # Get products with this category
        products = df[df['Category'] == category]
        
        # Analyze product titles
        for _, row in products.iterrows():
            title = row['Title'].lower()
            found_patterns = []
            
            # Look for clothing keywords
            for category_type, keywords in clothing_keywords.items():
                for keyword in keywords:
                    if keyword in title:
                        found_patterns.append((category_type, keyword))
            
            if found_patterns:
                product_patterns[category].append({
                    'title': row['Title'],
                    'handle': row['Handle'],
                    'patterns': found_patterns
                })
    
    return product_patterns

def test_category_normalization():
    """Test category normalization with sample data"""
    
    # Get test file path
    project_root = Path(__file__).parent.parent
    test_file = project_root / 'tests/test_data/sample csv matrixify/products_test_for_re_import.csv'
    output_file = project_root / 'data/intermediate/normalized_categories.csv'
    
    # Process CSV
    logger.info(f"Testing with file: {test_file}")
    df, report = process_csv(str(test_file), str(output_file))
    
    # Print category changes
    if report['changes']:
        logger.info("\nCategory Changes:")
        for change in report['changes']:
            logger.info(f"\nProduct: {change['Handle']}")
            logger.info(f"Title: {change['Title']}")
            logger.info(f"  Old Category: {change['Old Category'] if change['Old Category'] != 'None' else 'Not Set'}")
            logger.info(f"  New Category: {change['New Category']}")
            logger.info(f"  Change Type: {change['Change Type']}")
    
    # Print category statistics
    logger.info("\nCategory Statistics:")
    for category, count in report['category_stats'].items():
        logger.info(f"{category}: {count} products")
    
    # Print summary
    logger.info("\nSummary:")
    logger.info(f"Total products processed: {len(df['Handle'].unique())}")
    logger.info(f"Total changes made: {len(report['changes'])}")
    logger.info(f"Total unrecognized: {len(report['unrecognized'])}")
    
    # Calculate recognition rate
    total_products = len(df['Handle'].unique())
    recognized = total_products - len(report['unrecognized'])
    recognition_rate = (recognized / total_products * 100) if total_products > 0 else 0
    logger.info(f"Recognition rate: {recognition_rate:.1f}%")

if __name__ == '__main__':
    test_category_normalization() 