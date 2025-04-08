import sys
import logging
from pathlib import Path
import os
from typing import List, Dict, Optional, Tuple
import pandas as pd
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from api.client import ShopifyClient
from api.color_metaobject_creator import ColorMetaobjectCreator
from api.metaobject_registry import MetaobjectRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_test_data(file_path: str = None) -> List[Dict]:
    """Load color metaobject data from CSV"""
    try:
        if file_path:
            test_file = Path(file_path)
        else:
            test_file = project_root / 'tests/test_data/admin_api/Metaobject Test - Sheet1.csv'
            
        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file}")
            
        logger.info(f"Loading test data from: {test_file}")
        df = pd.read_csv(test_file)
        
        # Log DataFrame info
        logger.info(f"Loaded CSV with {len(df)} rows")
        logger.info(f"Columns: {', '.join(df.columns)}")
        
        # Group by Handle to collect all fields for each color
        color_data_list = []
        for handle, group in df.groupby('Handle'):
            color_data = {
                'handle': handle,
                'name': None,
                'hex': None,
                'color_taxonomy': None,
                'pattern_taxonomy': None,
                'fields': []  # Store raw field data for debugging
            }
            
            # Process each field for the color
            for _, row in group.iterrows():
                field = row['Field'].lower()
                value = row['Value']
                color_data['fields'].append({'key': field, 'value': value})
                
                if field == 'label':
                    color_data['name'] = value
                elif field == 'color':
                    color_data['hex'] = value
                elif field == 'color_taxonomy_reference':
                    color_data['color_taxonomy'] = value
                elif field == 'pattern_taxonomy_reference':
                    color_data['pattern_taxonomy'] = value
            
            color_data_list.append(color_data)
            logger.debug(f"Added color: {json.dumps(color_data, indent=2)}")
            
        logger.info(f"Found {len(color_data_list)} unique colors")
        
        # Validate required fields
        for color in color_data_list:
            missing = [k for k, v in color.items() if v is None and k != 'fields']
            if missing:
                logger.warning(f"Color {color['handle']} missing fields: {missing}")
            
        return color_data_list
        
    except Exception as e:
        logger.error(f"Error loading test data: {e}")
        raise

def test_metaobject_definition(client: ShopifyClient):
    """Test fetching metaobject definition"""
    try:
        definitions = client.get_metaobject_definitions()
        logger.info("\nAvailable Metaobject Definitions:")
        for definition in definitions:
            logger.info(f"\nType: {definition['type']}")
            logger.info(f"Name: {definition['name']}")
            logger.info("Fields:")
            for field in definition.get('fieldDefinitions', []):
                logger.info(f"- {field['key']} ({field['type']['name']})")
        return True
    except Exception as e:
        logger.error(f"Failed to fetch definitions: {e}")
        return False

def test_single_color(client: ShopifyClient, color_data: Dict, dry_run: bool = True):
    """Test creating a single color metaobject"""
    try:
        if dry_run:
            logger.info(f"\nWould create metaobject:")
            logger.info(json.dumps({
                "type": "shopify--color-pattern",
                "handle": color_data['handle'],
                "fields": color_data['fields']
            }, indent=2))
            return True
            
        created = client.create_metaobjects_batch(
            "shopify--color-pattern",
            [{
                "handle": color_data['handle'],
                "fields": color_data['fields']
            }]
        )
        
        return bool(created)
        
    except Exception as e:
        logger.error(f"Failed to test single color: {e}")
        return False

def test_color_metaobjects(test_file: Optional[str] = None, dry_run: bool = True) -> Tuple[int, int]:
    """Test creating color metaobjects and connecting to products"""
    client = ShopifyClient()
    
    # Get available definitions
    definitions = client.get_metaobject_definitions()
    logger.info("\nAvailable Metaobject Definitions:")
    for definition in definitions:
        logger.info(f"\nType: {definition['type']}")
        logger.info(f"Name: {definition['name']}")
        logger.info("Fields:")
        for field in definition.get('fieldDefinitions', []):
            logger.info(f"- {field['key']} ({field['type']['name']})")
    
    # Load test data
    color_data_list = load_test_data(test_file)
    logger.info(f"Loaded {len(color_data_list)} colors for testing")
    
    # Test with first color
    first_color = color_data_list[0]
    logger.info("\nTesting with first color:")
    logger.info(f"Name: {first_color['name']}")
    logger.info(f"Handle: {first_color['handle']}")
    logger.info(f"Fields: {json.dumps(first_color['fields'], indent=2)}")
    
    if dry_run:
        logger.info("\nDRY RUN - Would create metaobjects:")
        for color in color_data_list:
            logger.info(f"- {color['handle']}")
        return len(color_data_list), 0
    
    # Create metaobjects
    created, skipped = client.create_metaobjects_batch(
        "shopify--color-pattern",
        color_data_list
    )
    
    if skipped:
        logger.info(f"\nSkipped {len(skipped)} existing metaobjects:")
        for handle in skipped:
            logger.info(f"- {handle}")
    
    # Build product-color mapping
    product_color_map = {}
    for color in color_data_list:
        # Get the metaobject ID for this color
        color_id = client.get_color_metaobject_id(color['handle'])
        if not color_id:
            logger.error(f"Could not find metaobject ID for color: {color['handle']}")
            continue
            
        # Find products with this color
        # TODO: Implement your product-color matching logic here
        # For example:
        # products = client.find_products_by_color(color['name'])
        # for product in products:
        #     product_color_map[product['id']] = color_id
    
    if product_color_map:
        logger.info(f"\nConnecting {len(product_color_map)} products to colors...")
        success, errors = client.bulk_connect_product_colors(product_color_map)
        
        logger.info(f"\n✅ Connected {success} products to colors")
        if errors > 0:
            logger.warning(f"⚠️ Failed to connect {errors} products")
    else:
        logger.warning("\nNo product-color connections to make")
    
    return len(created), len(skipped)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test color metaobject creation')
    parser.add_argument('--file', type=str,
                       help='Path to test CSV file')
    parser.add_argument('--live', action='store_true', 
                       help='Run in live mode (actually create metaobjects)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        created, skipped = test_color_metaobjects(
            test_file=args.file,
            dry_run=not args.live
        )
        
        if created > 0:
            logger.info(f"\n✅ Successfully created {created} new metaobjects")
        if skipped > 0:
            logger.info(f"⏭️ Skipped {skipped} existing metaobjects")
            
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        sys.exit(1) 