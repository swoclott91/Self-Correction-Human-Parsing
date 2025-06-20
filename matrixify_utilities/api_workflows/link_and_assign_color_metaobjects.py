import pandas as pd
import sys
from pathlib import Path
import os
import logging
from typing import Optional, Dict
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from matrixify_utilities.interface.variant_source import VariantSource
from matrixify_utilities.interface.metafield_writer import MetafieldWriter

def get_metaobject_handle_from_reference(reference: str) -> Optional[str]:
    """
    Extract the handle portion from a metaobject reference.
    
    Args:
        reference: Full metaobject reference (e.g., "shopify--color-pattern.pumpkin-b66142")
        
    Returns:
        The handle portion if valid, None otherwise
    """
    if not reference or reference == 'nan':
        return None
        
    # Handle both formats:
    # - Full reference: "shopify--color-pattern.pumpkin-b66142"
    # - Just handle: "pumpkin-b66142"
    parts = reference.split('.')
    
    if len(parts) == 2:
        type_prefix, handle = parts
        if type_prefix != "shopify--color-pattern":
            logger.warning(f"Unexpected type prefix: {type_prefix}")
            return None
        logger.debug(f"Extracted handle '{handle}' from reference '{reference}'")
        return handle
    elif len(parts) == 1:
        handle = parts[0]
        logger.debug(f"Using handle directly: {handle}")
        return handle
    else:
        logger.warning(f"Invalid reference format: {reference}")
        return None

def run_color_link_and_assign(csv_path: str):
    """
    Links color metaobjects to product option values using data from a Matrixify export.
    """
    csv_file = Path(csv_path)
    if not csv_file.is_absolute():
        csv_file = project_root / csv_path

    if not csv_file.exists():
        logger.error(f"CSV file not found at {csv_file}")
        return

    logger.info(f"Reading CSV from: {csv_file}")
    df = pd.read_csv(csv_file)
    writer = MetafieldWriter()
    variant_fetcher = VariantSource()

    # First, build a map of color -> metaobject reference
    color_references: Dict[str, str] = {}
    for _, row in df.iterrows():
        color = str(row['Option1 Value']).strip()
        reference = str(row['Metafield: shopify.color-pattern [list.metaobject_reference]'])
        
        # Only store valid references
        if reference and reference != 'nan':
            if color not in color_references:
                color_references[color] = reference
                logger.info(f"Found reference for {color}: {reference}")

    # Now process all variants
    for _, row in df.iterrows():
        try:
            product_id = f"gid://shopify/Product/{int(row['ID'])}"
            variant_id = f"gid://shopify/ProductVariant/{int(row['Variant ID'])}"
            color_label = str(row['Option1 Value']).strip()
            
            # Get the reference for this color
            color_reference = color_references.get(color_label)
            if not color_reference:
                logger.warning(f"No reference found for color: {color_label}")
                continue

            logger.info(f"\nProcessing variant {variant_id}")
            logger.info(f"  Color: {color_label}")
            logger.info(f"  Using reference: {color_reference}")
            
            # Get the handle from the reference
            color_handle = get_metaobject_handle_from_reference(color_reference)
            if not color_handle:
                logger.warning(f"  Invalid reference format: {color_reference}")
                continue
                
            logger.info(f"  Looking up metaobject with handle: {color_handle}")
            existing_metaobject = writer.get_metaobject_by_handle(color_handle)
            
            if existing_metaobject:
                logger.info(f"  Using existing metaobject: {existing_metaobject}")
                metaobject_gid = existing_metaobject
            else:
                logger.warning(f"  Expected metaobject not found: {color_handle}")
                continue

            # Get option IDs
            logger.info(f"  Getting color option IDs for product")
            option_info = variant_fetcher.get_color_option_ids(product_id, color_label)
            color_option_id = option_info['color_option_id']
            color_option_value_id = option_info['color_option_value_id']
            logger.info(f"  Found option IDs: {color_option_id} -> {color_option_value_id}")

            # Link the metaobject
            logger.info(f"  Linking metaobject to option value")
            result = writer.attach_color_to_variant_option_value(
                product_id=product_id,
                option_id=color_option_id,
                option_value_id=color_option_value_id,
                metaobject_gid=metaobject_gid
            )

            if result.get("errors") or result.get("data", {}).get("productOptionUpdate", {}).get("userErrors"):
                logger.error(f"❌ Error linking {color_label}: {result}")
            else:
                logger.info(f"✅ Successfully linked {color_label}")

        except Exception as e:
            logger.error(f"❌ Failed to process variant {variant_id}: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)

if __name__ == "__main__":
    csv_path = os.getenv(
        "MATRIXIFY_CSV_PATH", 
        "matrixify_utilities/data/normalized_products.csv"
    )
    run_color_link_and_assign(csv_path)
