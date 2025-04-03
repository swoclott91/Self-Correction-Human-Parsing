import pandas as pd
from normalize_sizes import process_csv
import logging
from pathlib import Path
import os
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def ensure_directory_exists(path: Path):
    """Create directory if it doesn't exist, clear if it does"""
    if path.exists():
        # Remove directory and contents
        shutil.rmtree(path)
    path.mkdir(parents=True)

def test_multiple_colors():
    """Test size normalization with multiple color variants"""
    
    # Get test file path
    project_root = Path(__file__).parent.parent
    test_file = project_root / 'tests/test_data/sample csv matrixify/products_test_for_re_import.csv'
    
    # Create fresh output directories
    output_dir = project_root / 'data/intermediate'
    reports_dir = project_root / 'data/reports'
    
    try:
        ensure_directory_exists(output_dir)
        ensure_directory_exists(reports_dir)
        
        output_file = output_dir / 'normalized_sizes.csv'
        
        # Process CSV
        logger.info(f"Testing with file: {test_file}")
        result = process_csv(str(test_file), str(output_file))
        
        # Verify results
        logger.info("\nVerifying results...")
        
        # Group by product and color to check metafield placement
        for (handle, color), group in result.groupby(['Handle', 'Option1 Value']):
            metafield_values = group['Metafield: shopify.size [list.metaobject_reference]'].values
            
            # First variant should have metafield, others should be empty
            if len(metafield_values) > 0:
                logger.info(f"\nProduct: {handle}")
                logger.info(f"Color: {color}")
                logger.info(f"First variant metafield: {metafield_values[0]}")
                if len(metafield_values) > 1:
                    logger.info(f"Other variants empty: {all(pd.isna(v) or v == '' for v in metafield_values[1:])}")
    
    except PermissionError as e:
        logger.error(f"Permission error: {e}")
        logger.info("Try closing any open files and running again")
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        raise

if __name__ == '__main__':
    test_multiple_colors() 