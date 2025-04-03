import pandas as pd
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_size_normalization():
    """Test size normalization with sample data"""
    
    # Test data based on the CSV
    test_data = {
        'Handle': ['hyfve-raw-edge-button-down-raglan-sleeve-shirt'] * 3,
        'Option1 Name': ['Size'] * 3,
        'Option1 Value': ['Large', 'Small', 'Medium'],
        'Metafield: shopify.size [list.metaobject_reference]': [''] * 3
    }
    
    # Create test DataFrame
    df = pd.DataFrame(test_data)
    
    logger.info("\nInput Data:")
    logger.info(df[['Handle', 'Option1 Name', 'Option1 Value']].to_string())
    
    # Import and process
    try:
        from normalize_sizes import process_csv
        result = process_csv(df)
        
        logger.info("\nNormalized Values:")
        logger.info(result[['Option1 Value']].to_string())
        
        logger.info("\nMetafield Values:")
        logger.info(result['Metafield: shopify.size [list.metaobject_reference]'].iloc[0])
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == '__main__':
    # Project setup
    project_root = Path(__file__).parent.parent
    
    # Run test
    test_size_normalization() 