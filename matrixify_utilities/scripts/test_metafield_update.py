import logging
from pathlib import Path
import pandas as pd
from api.category_updater import CategoryUpdater
from api.metafield_updater import MetafieldUpdater

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_metafield_update():
    """Test updating product metafields with metaobject references"""
    
    # Load sample data
    csv_path = Path(__file__).parent.parent / 'tests/test_data/sample csv matrixify/products_multiple_colors.csv'
    df = pd.read_csv(csv_path)
    
    # Get metafield columns
    metafield_cols = [col for col in df.columns if col.startswith('Metafield:')]
    logger.info(f"\nFound metafield columns:")
    for col in metafield_cols:
        logger.info(f"  {col}")
    
    # Show sample values
    sample_row = df.iloc[0]
    logger.info(f"\nSample metafield values:")
    for col in metafield_cols:
        if pd.notna(sample_row[col]):
            logger.info(f"  {col}: {sample_row[col]}")
    
    # Initialize updater
    updater = MetafieldUpdater()
    
    # Get available metaobjects
    metaobjects = updater.get_metaobject_definitions()
    logger.info(f"\nAvailable metaobject types:")
    for obj_type, data in metaobjects.items():
        logger.info(f"  {obj_type}: {len(data['values'])} values")
        if len(data['values']) > 0:
            sample_value = next(iter(data['values'].items()))
            logger.info(f"    Sample: {sample_value[0]} -> {sample_value[1]}")
    
    # Test update with sample values
    test_product_id = "14697143894388"  # Use your test product ID
    test_metafields = {
        'fabric': 'shopify--fabric.cotton, shopify--fabric.polyester',
        'color_pattern': 'shopify--color-pattern.black',
        'size': 'shopify--size.s, shopify--size.m, shopify--size.l',
        'care_instructions': 'shopify--care-instructions.machine-wash'
    }
    
    logger.info(f"\nTesting update with:")
    for key, value in test_metafields.items():
        logger.info(f"  {key}: {value}")
        
    result = updater.update_product_metafields(test_product_id, test_metafields)
    
    # Show results
    if result.get('data', {}).get('productUpdate', {}).get('userErrors'):
        logger.error("Update failed with errors:")
        for error in result['data']['productUpdate']['userErrors']:
            logger.error(f"  {error['message']}")
    else:
        logger.info("\nUpdate successful!")
        metafields = result.get('data', {}).get('productUpdate', {}).get('product', {}).get('metafields', {}).get('nodes', [])
        for mf in metafields:
            logger.info(f"  {mf['namespace']}.{mf['key']}: {mf['value']}")

if __name__ == '__main__':
    test_metafield_update() 