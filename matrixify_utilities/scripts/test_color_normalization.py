from normalize_colors import process_colors
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def test_color_normalization():
    """Test color normalization with sample data"""
    
    # Get test file path
    project_root = Path(__file__).parent.parent
    test_file = project_root / 'tests/test_data/sample csv matrixify/products_test_for_re_import.csv'
    output_dir = project_root / 'data/intermediate'
    
    # Process colors
    products_df, metaobjects_df = process_colors(str(test_file), str(output_dir))
    
    # Print summary
    logger.info("\nColor Processing Summary:")
    logger.info(f"Total products processed: {len(products_df['Handle'].unique())}")
    logger.info(f"Total variants processed: {len(products_df)}")
    logger.info(f"Unique colors created: {len(metaobjects_df)}")

if __name__ == '__main__':
    test_color_normalization()