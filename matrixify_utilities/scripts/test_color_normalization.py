import sys
import logging
from pathlib import Path

# Add environment check
def check_environment():
    try:
        import pandas as pd
        import numpy as np
        import torch
        import cv2
        logging.info(f"Python version: {sys.version}")
        logging.info(f"Pandas version: {pd.__version__}")
        logging.info(f"NumPy version: {np.__version__}")
        logging.info(f"PyTorch version: {torch.__version__}")
        logging.info(f"OpenCV version: {cv2.__version__}")
    except ImportError as e:
        logging.error(f"Missing dependency: {str(e)}")
        sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add environment check before imports
check_environment()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from scripts.normalize_colors import process_colors
from utils.garment_parser import GarmentParser
from utils.color_utils import ColorExtractor
from utils.palette_classifier import PaletteClassifier

def test_color_normalization():
    """Test color normalization with sample data"""
    
    # Get test file path
    test_file = project_root / 'tests/test_data/sample csv matrixify/products_test_for_re_import.csv'
    output_dir = project_root / 'data/intermediate'
    
    logger.info(f"Processing file: {test_file}")
    
    # Process colors
    products_df, metaobjects_df = process_colors(str(test_file), str(output_dir))
    
    # Debug output
    logger.info("\nDEBUG: Color Metaobjects")
    if not metaobjects_df.empty:
        for _, row in metaobjects_df.iterrows():
            logger.info(f"Handle: {row['Handle']}")
            logger.info(f"Field: {row['Field']}")
            logger.info(f"Value: {row['Value']}")
            logger.info("---")
    
    # Debug output
    logger.info("\nDEBUG: First few product rows")
    if not products_df.empty:
        sample = products_df.head()
        for _, row in sample.iterrows():
            logger.info(f"Product: {row['Title']}")
            logger.info(f"Color: {row['Option1 Value']}")
            logger.info(f"Color Pattern Handle: {row.get('Metafield: shopify.color-pattern [list.metaobject_reference]', 'Not Set')}")
            logger.info("---")

if __name__ == '__main__':
    test_color_normalization()