import pandas as pd
import logging
from pathlib import Path
from typing import Union, Dict, List, Tuple
from collections import defaultdict
import numpy as np
import cv2

# Import our custom modules
from simple_extractor import GarmentParser
from utils.color_utils import ColorExtractor, ColorInfo
from palette_classifier import PaletteClassifier

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class ColorNormalizer:
    def __init__(self):
        self.color_stats = defaultdict(int)
        self.palette_classifier = PaletteClassifier()
        self.color_extractor = ColorExtractor(n_colors=5, lab_threshold=20)
        self.parser = GarmentParser(
            model_path='models/exp-schp-201908301523-atr.pth',
            dataset='atr'
        )
        
        # Load Shopify color taxonomy
        self.color_taxonomy = self.load_color_taxonomy()
        
    @staticmethod
    def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
        """Convert hex color code to RGB tuple"""
        hex_code = hex_code.lstrip('#')
        return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def _rgb_to_hsv(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """Convert RGB to HSV color space"""
        bgr = np.uint8([[list(reversed(rgb))]])
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0][0]
        h, s, v = hsv
        # Normalize values
        h = h * 2  # OpenCV H is 0-180, convert to 0-360
        s = s / 255 * 100  # Convert to percentage
        v = v / 255 * 100  # Convert to percentage
        return (h, s, v)

    def process_csv(self, input_data: Union[str, pd.DataFrame], output_path: str = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Process Matrixify CSV and create color metaobjects"""
        
        # Load data
        if isinstance(input_data, str):
            df = pd.read_csv(input_data)
        else:
            df = input_data.copy()
        
        # Initialize tracking
        metaobject_rows = []
        color_changes = []
        
        # Process unique products
        unique_products = df.drop_duplicates('Handle')[['Handle', 'Title', 'Category']]
        
        for _, row in unique_products.iterrows():
            handle = row['Handle']
            title = row['Title']
            
            # Get product variants
            variants = df[df['Handle'] == handle]
            
            # Process each variant's color
            for _, variant in variants.iterrows():
                if 'Option1 Name' in variant and variant['Option1 Name'].lower() == 'color':
                    color_name = variant['Option1 Value']
                    
                    # Create color handle
                    color_handle = color_name.lower().replace(' ', '-')
                    
                    # Extract colors from image
                    if 'Variant Image' in variant:
                        image_path = variant['Variant Image']
                        
                        # Parse image and get mask
                        result = self.parser.parse_image(image_path)
                        mask = self.parser.get_garment_mask(result)
                        
                        # Extract colors
                        color_analysis = self.color_extractor.extract_colors(image_path, mask)
                        
                        # Get primary color hex
                        primary_color = color_analysis['colors'][0]
                        hex_code = primary_color.hex
                        
                        # Map to Shopify taxonomy color
                        taxonomy_color = self.map_to_shopify_color(color_name, hex_code)
                        
                        # Create metaobject rows
                        metaobject_rows.extend([
                            {
                                'Handle': color_handle,
                                'Command': 'MERGE',
                                'Definition: Name': 'Color',
                                'Field': 'label',
                                'Value': color_name  # Use original color name for label
                            },
                            {
                                'Handle': color_handle,
                                'Command': 'MERGE',
                                'Definition: Name': 'Color',
                                'Field': 'color',
                                'Value': hex_code  # Use extracted hex code
                            },
                            {
                                'Handle': color_handle,
                                'Command': 'MERGE',
                                'Definition: Name': 'Color',
                                'Field': 'color_taxonomy_reference',
                                'Value': taxonomy_color  # Use mapped taxonomy value
                            },
                            {
                                'Handle': color_handle,
                                'Command': 'MERGE',
                                'Definition: Name': 'Color',
                                'Field': 'pattern_taxonomy_reference',
                                'Value': 'gid://shopify/TaxonomyValue/2874'  # Solid pattern
                            }
                        ])
                        
                        # Update variant with color metaobject reference
                        df.loc[variant.name, 'Variant Metafield: custom.color_palette [metaobject_reference]'] = color_handle
                        
                        # Track change
                        color_changes.append({
                            'Handle': handle,
                            'Variant': variant.name,
                            'Color': color_name,
                            'Hex': hex_code,
                            'Taxonomy': taxonomy_color
                        })
        
        # Create metaobjects DataFrame
        metaobjects_df = pd.DataFrame(metaobject_rows)
        
        # Save files
        if output_path:
            df.to_csv(output_path, index=False)
            
            # Save metaobjects to separate file
            metaobjects_path = Path(output_path).parent / 'color_metaobjects.csv'
            metaobjects_df.to_csv(metaobjects_path, index=False)
            
            # Save changes report
            changes_df = pd.DataFrame(color_changes)
            changes_path = Path(output_path).parent / 'color_changes.csv'
            changes_df.to_csv(changes_path, index=False)
        
        return df, metaobjects_df

    def generate_color_id(self, color_name: str, hex_code: str) -> str:
        """Generate a unique ID for a color metaobject"""
        # Create a deterministic but unique ID based on color name and hex code
        # Use same format as category IDs but with 'color' prefix
        clean_name = ''.join(c.lower() for c in color_name if c.isalnum())
        return f"color-{clean_name}-{hex_code.replace('#', '')}"

    def map_to_shopify_color(self, color_name: str, hex_code: str) -> str:
        """Map a color name to the closest Shopify taxonomy color"""
        color_lower = color_name.lower()
        
        # Direct mappings
        direct_mappings = {
            'white': 'gid://shopify/TaxonomyValue/3',
            'black': 'gid://shopify/TaxonomyValue/1',
            'blue': 'gid://shopify/TaxonomyValue/2',
            'bronze': 'gid://shopify/TaxonomyValue/657',
            'brown': 'gid://shopify/TaxonomyValue/7',
            'clear': 'gid://shopify/TaxonomyValue/17',
            'gold': 'gid://shopify/TaxonomyValue/4',
            'gray': 'gid://shopify/TaxonomyValue/8',
            'grey': 'gid://shopify/TaxonomyValue/8',
            'green': 'gid://shopify/TaxonomyValue/9',
            'navy': 'gid://shopify/TaxonomyValue/15',
            'orange': 'gid://shopify/TaxonomyValue/10',
            'pink': 'gid://shopify/TaxonomyValue/11',
            'purple': 'gid://shopify/TaxonomyValue/12',
            'red': 'gid://shopify/TaxonomyValue/13',
            'rose gold': 'gid://shopify/TaxonomyValue/16',
            'silver': 'gid://shopify/TaxonomyValue/5',
            'yellow': 'gid://shopify/TaxonomyValue/14',
        }
        
        # Check compound color names
        for base_color, taxonomy_id in direct_mappings.items():
            if base_color in color_lower:
                return taxonomy_id
        
        # If no direct match, use color analysis to determine closest base color
        rgb = self.hex_to_rgb(hex_code)
        hsv = self._rgb_to_hsv(rgb)
        h, s, v = hsv
        
        # Very low saturation = neutral colors
        if s < 0.2:
            if v < 0.3:
                return direct_mappings['black']
            elif v > 0.7:
                return direct_mappings['white']
            else:
                return direct_mappings['gray']
        
        # Map HSV to basic colors
        if 0 <= h <= 30 or 330 <= h <= 360:
            return direct_mappings['red']
        elif 30 < h <= 90:
            return direct_mappings['yellow']
        elif 90 < h <= 150:
            return direct_mappings['green']
        elif 150 < h <= 210:
            return direct_mappings['blue']
        elif 210 < h <= 270:
            return direct_mappings['purple']
        elif 270 < h <= 330:
            return direct_mappings['pink']
        
        # Fallback to multicolor
        return 'gid://shopify/TaxonomyValue/2865'

def process_colors(input_file: str, output_dir: str):
    """Process colors in a Matrixify CSV file"""
    # Initialize components
    parser = GarmentParser(
        model_path='models/exp-schp-201908301523-atr.pth',
        dataset='atr'
    )
    color_extractor = ColorExtractor(n_colors=5, lab_threshold=20)
    palette_classifier = PaletteClassifier()
    normalizer = ColorNormalizer()
    
    # Process CSV
    products_df, metaobjects_df = normalizer.process_csv(
        input_file,
        output_path=Path(output_dir) / 'normalized_products.csv'
    )
    
    return products_df, metaobjects_df 