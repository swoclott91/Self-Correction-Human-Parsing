import pandas as pd
import logging
from pathlib import Path
import re
from typing import Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

class SizeNormalizer:
    def __init__(self):
        # Standard size mappings
        self.size_mappings = {
            # Letter sizes
            r'(?i)^extra\s*small$': 'XS',
            r'(?i)^x-small$': 'XS',
            r'(?i)^small$': 'S',
            r'(?i)^medium$': 'M',
            r'(?i)^large$': 'L',
            r'(?i)^x-large$': 'XL',
            r'(?i)^extra\s*large$': 'XL',
            r'(?i)^2xl$': '2XL',
            r'(?i)^xxl$': '2XL',
            r'(?i)^3xl$': '3XL',
            r'(?i)^xxxl$': '3XL',
            
            # Numeric sizes
            r'(?i)^size\s*(\d+)$': r'\1',  # Convert "Size 8" to "8"
            r'(?i)^(\d+)\s*$': r'\1',      # Keep clean numbers as is
            
            # Special cases
            r'(?i)^one\s*size$': 'OS',
            r'(?i)^o/s$': 'OS',
            r'(?i)^free\s*size$': 'OS',
            r'(?i)^universal$': 'OS',
        }
        
        # Metafield handle mappings
        self.metafield_handles = {
            'XS': 'shopify--size.xs',
            'S': 'shopify--size.s',
            'M': 'shopify--size.m',
            'L': 'shopify--size.l',
            'XL': 'shopify--size.xl',
            '2XL': 'shopify--size.2xl',
            '3XL': 'shopify--size.3xl',
            'OS': 'shopify--size.one-size',
        }
        
        # Add numeric sizes 00-20
        for size in range(0, 21):
            size_str = f"{size:02d}" if size < 10 else str(size)
            self.metafield_handles[str(size)] = f"shopify--size.{size_str}"
        
        # Add size order for sorting
        self.size_order = {
            'XXS': 0, 'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 
            '2XL': 6, '3XL': 7, 'OS': 99
        }
        # Add numeric sizes
        for size in range(0, 21):
            self.size_order[str(size)] = size + 20  # After letter sizes

    def normalize_size(self, size_value: str) -> str:
        """Normalize a size value to standard format"""
        if not isinstance(size_value, str):
            return size_value
            
        size_value = size_value.strip()
        
        # Try each mapping pattern
        for pattern, replacement in self.size_mappings.items():
            match = re.match(pattern, size_value)
            if match:
                # If the pattern has groups, use them in replacement
                if match.groups():
                    return re.sub(pattern, replacement, size_value)
                return replacement
                
        # If no match found, return original
        return size_value

    def get_metafield_handle(self, normalized_size: str) -> str:
        """Get metafield handle for a normalized size"""
        return self.metafield_handles.get(normalized_size, '')

def process_csv(input_data: Union[str, pd.DataFrame], output_path: str = None):
    """Process Matrixify CSV and normalize sizes"""
    logger.info("Processing size normalization")
    
    # Handle input
    if isinstance(input_data, str):
        df = pd.read_csv(input_data)
    else:
        df = input_data.copy()
    
    # Initialize normalizer
    normalizer = SizeNormalizer()
    
    # Track changes
    changes = []
    
    # First group by product handle
    for handle, product_group in df.groupby('Handle'):
        # Check if product has a valid category
        first_row = product_group.iloc[0]
        has_category = (
            pd.notna(first_row.get('Category')) and 
            'Apparel & Accessories > Clothing' in str(first_row.get('Category'))
        )
        
        if not has_category:
            logger.warning(f"Skipping {handle}: No valid clothing category assigned")
            continue
            
        # Get all sizes for this product across all colors
        all_sizes = []
        
        # Process each variant
        for idx, row in product_group.iterrows():
            # Check if row has size option
            size_value = None
            if 'Option2 Name' in row and row['Option2 Name'] == 'Size':
                old_size = row['Option2 Value']
                new_size = normalizer.normalize_size(old_size)
                if old_size != new_size:
                    changes.append({
                        'Handle': handle,
                        'Color': row['Option1 Value'],
                        'Old Size': old_size,
                        'New Size': new_size
                    })
                    df.at[idx, 'Option2 Value'] = new_size
                size_value = new_size
            
            if size_value:
                all_sizes.append(size_value)
        
        # Create single metafield value for all product sizes
        if all_sizes:
            # Get unique sizes in order of appearance
            unique_sizes = []
            for size in all_sizes:
                if size not in unique_sizes:
                    unique_sizes.append(size)
            
            metafield_value = ', '.join(
                normalizer.get_metafield_handle(size) for size in unique_sizes
            )
            
            # Add product-level metafield to first row only
            first_row_idx = product_group.index[0]
            df.loc[first_row_idx, 'Metafield: shopify.size [list.metaobject_reference]'] = metafield_value
            
            # Clear metafield for other rows
            other_row_indices = product_group.index[1:]
            df.loc[other_row_indices, 'Metafield: shopify.size [list.metaobject_reference]'] = ''
    
    # Save changes report
    if changes:
        changes_df = pd.DataFrame(changes)
        
        # Create reports directory if it doesn't exist
        project_root = Path(__file__).parent.parent
        reports_dir = project_root / 'data' / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Save changes report
        changes_path = reports_dir / 'size_normalization_changes.csv'
        changes_df.to_csv(changes_path, index=False)
        logger.info(f"Saved changes report to {changes_path}")
        
        # Print summary
        logger.info("\nSize Normalization Summary:")
        logger.info(f"Total changes: {len(changes)}")
        logger.info("\nSample changes:")
        for change in changes[:5]:
            logger.info(f"{change['Handle']} ({change['Color']}): {change['Old Size']} -> {change['New Size']}")
    
    # Save normalized CSV
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"Saved normalized CSV to {output_path}")
    
    return df

if __name__ == '__main__':
    # Setup paths
    project_root = Path(__file__).parent.parent
    input_csv = project_root / 'data/exports/products and variants.csv'
    output_csv = project_root / 'data/intermediate/normalized_sizes.csv'
    
    # Create output directory if needed
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    
    # Process CSV
    process_csv(str(input_csv), str(output_csv)) 