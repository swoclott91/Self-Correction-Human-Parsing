import pandas as pd
import logging
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configure logging
logger = logging.getLogger(__name__)

def validate_csv(file_path: str) -> dict:
    """
    Validate the processed CSV file
    
    Args:
        file_path: Path to CSV file to validate
    
    Returns:
        dict with validation results:
        {
            'is_valid': bool,
            'errors': list of error messages
        }
    """
    errors = []
    try:
        # Load the CSV
        df = pd.read_csv(file_path)
        
        # Required columns - updated to essential fields only
        required_columns = [
            'Handle',  # Product/variant handle
            'Title',   # Product title
            'Option1 Name',  # Color option name
            'Option1 Value', # Color value
            'Variant Image' # Required for color analysis
        ]
        
        # Check for required columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Check for empty handles
        if df['Handle'].isnull().any():
            errors.append("Found rows with missing Handle values")
        
        # Check for duplicate handles + option combinations
        option_cols = [col for col in df.columns if col.startswith('Option') and col.endswith('Value')]
        if option_cols:
            dupes = df.duplicated(['Handle'] + option_cols, keep=False)
            if dupes.any():
                dupe_handles = df[dupes]['Handle'].unique()
                errors.append(f"Found duplicate Handle + Option combinations for: {', '.join(dupe_handles)}")
        
        # Check for missing images where required
        color_variants = df[df['Option1 Name'] == 'Color']
        if len(color_variants) > 0 and color_variants['Variant Image'].isnull().any():
            errors.append("Found color variants missing images")
        
        # Check for required metafields
        metafield_cols = [
            'Metafield: shopify.color-pattern [list.metaobject_reference]',
            'Variant Metafield: custom.pallet [list.metaobject_reference]'
        ]
        for col in metafield_cols:
            if col not in df.columns:
                errors.append(f"Missing metafield column: {col}")
        
        # Log validation results
        if errors:
            logger.warning("Validation failed with the following errors:")
            for error in errors:
                logger.warning(f"- {error}")
        else:
            logger.info("CSV validation passed")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Error validating CSV: {str(e)}")
        return {
            'is_valid': False,
            'errors': [f"Validation error: {str(e)}"]
        }

if __name__ == '__main__':
    # Test the validator
    test_file = project_root / 'tests/test_data/sample csv matrixify/products_test_for_re_import.csv'
    results = validate_csv(str(test_file))
    
    if results['is_valid']:
        print("Validation passed!")
    else:
        print("Validation failed:")
        for error in results['errors']:
            print(f"- {error}") 