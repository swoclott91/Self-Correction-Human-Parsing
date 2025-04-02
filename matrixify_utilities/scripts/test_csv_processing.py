import os
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def debug_module_structure():
    """Check critical module structure"""
    logger.info("\nChecking module structure:")
    
    critical_files = [
        project_root / 'utils/networks/modules/__init__.py',
        project_root / 'utils/networks/backbone/resnet.py',
        project_root / 'utils/networks/context_encoding/__init__.py',
        project_root / 'utils/networks/AugmentCE2P.py'
    ]
    
    for path in critical_files:
        if path.exists():
            logger.info(f"✓ Found {path.relative_to(project_root)}")
        else:
            logger.error(f"✗ Missing {path.relative_to(project_root)}")

def test_csv():
    # Check module structure
    debug_module_structure()
    
    # Test CSV path
    test_csv = project_root / 'tests' / 'test_data' / 'sample csv matrixify' / 'products and variants.csv'
    
    if not test_csv.exists():
        logger.info(f"Looking for test CSV...")
        
        # Try alternate path
        alt_csv = Path(r"C:\Users\Shane Work\Documents\GitHub\Self-Correction-Human-Parsing\data\sample csv matrixify\products and variants.csv")
        if alt_csv.exists():
            test_csv = alt_csv
            logger.info(f"Found CSV at: {test_csv}")
        else:
            logger.error("Could not find CSV file")
            return
    
    logger.info(f"\nProcessing CSV: {test_csv}")
    try:
        from utils.garment_parser import GarmentParser
        from scripts.extract_variant_colors import process_shopify_csv
        
        results = process_shopify_csv(str(test_csv))
        logger.info("Processing complete!")
        if hasattr(results, 'shape'):
            logger.info(f"Processed {results.shape[0]} rows")
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)

if __name__ == '__main__':
    test_csv() 