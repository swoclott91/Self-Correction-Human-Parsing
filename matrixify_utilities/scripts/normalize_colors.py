import pandas as pd
import logging
from pathlib import Path
from typing import Union, Dict, List, Tuple
from collections import defaultdict
import numpy as np
import cv2
import sys
import requests
from urllib.parse import urlparse
import tempfile
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import our custom modules
from utils.garment_parser import GarmentParser
from utils.color_utils import ColorExtractor, ColorInfo
from utils.palette_classifier import PaletteClassifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent.parent / 'logs/color_processing.log')
    ]
)

# Create loggers
logger = logging.getLogger(__name__)
debug_logger = logging.getLogger('debug')
debug_logger.setLevel(logging.WARNING)  # Set to WARNING to suppress ABN debug output

# Suppress other verbose loggers
logging.getLogger('PIL').setLevel(logging.WARNING)
logging.getLogger('torch').setLevel(logging.WARNING)
logging.getLogger('networks').setLevel(logging.WARNING)

class ColorNormalizer:
    def __init__(self):
        self.color_stats = defaultdict(int)
        self.palette_classifier = PaletteClassifier()
        self.color_extractor = ColorExtractor(n_colors=5, lab_threshold=20)
        
        # Use absolute path to model
        model_path = str(Path(__file__).parent.parent / 'models' / 'exp-schp-201908301523-atr.pth')
        self.parser = GarmentParser(
            model_path=model_path,
            dataset='atr',
            verbose=False  # Turn off debugging output
        )
        
        # Load Shopify color taxonomy
        self.color_taxonomy = self.load_color_taxonomy()
        
        self.color_ranges = self.initialize_color_ranges()
        
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

    def download_image(self, url: str) -> str:
        """Download image from URL and save to temp file"""
        try:
            # Create temp directory if it doesn't exist
            temp_dir = Path(__file__).parent.parent / 'data' / 'temp'
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Clean URL and get filename
            url = url.replace('\\', '/')
            filename = os.path.basename(urlparse(url).path).split('?')[0]
            local_path = temp_dir / filename
            
            # Download if not already cached
            if not local_path.exists():
                response = requests.get(url)
                response.raise_for_status()
                
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Downloaded image to {local_path}")
            else:
                logger.info(f"Using cached image: {local_path}")
                
            return str(local_path)
            
        except Exception as e:
            logger.error(f"Failed to download image {url}: {e}")
            return None

    def initialize_color_ranges(self) -> Dict[str, Dict[str, Tuple[float, float]]]:
        """Define HSV ranges for basic color categories"""
        return {
            'red': {'h': (0, 30), 'h2': (330, 360), 's': (30, 100), 'v': (20, 100)},
            'green': {'h': (90, 150), 's': (30, 100), 'v': (20, 100)},
            'blue': {'h': (180, 270), 's': (30, 100), 'v': (20, 100)},
            # ... other colors ...
        }

    def color_confidence_score(self, hsv: Tuple[float, float, float], expected_color: str) -> float:
        """Calculate confidence score with shadow compensation"""
        h, s, v = hsv
        color_range = self.color_ranges.get(expected_color.lower())
        
        # Special handling for light colors
        if 'white' in expected_color.lower() or 'light' in expected_color.lower():
            # Boost confidence for lighter shades
            v_boost = min((v / 70) ** 1.5, 1.5)  # Exponential boost for higher values
            # Reduce impact of saturation for light colors
            s_penalty = max(1 - (s / 100) * 0.5, 0.5)  # Less penalty for saturation
            confidence = min(v_boost * s_penalty, 1.0)
            
            # Log confidence calculation for light colors
            logger.info(f"\nConfidence Scoring for {expected_color}:")
            logger.info(f"HSV Input: ({h:.1f}°, {s:.1f}%, {v:.1f}%)")
            logger.info(f"Value Boost: {v_boost:.2f}, Saturation Penalty: {s_penalty:.2f}")
            logger.info(f"Final Confidence: {confidence:.2f}")
            
            return confidence
        
        # Regular color handling
        if not color_range:
            return 1.0
        
        # Check if color is within primary or secondary hue range
        in_primary_range = color_range['h'][0] <= h <= color_range['h'][1]
        in_secondary_range = ('h2' in color_range and 
                            color_range['h2'][0] <= h <= color_range['h2'][1])
        
        if not (in_primary_range or in_secondary_range):
            return 0.5  # Color outside expected hue range
            
        # Check saturation and value ranges
        s_score = 1.0 if color_range['s'][0] <= s <= color_range['s'][1] else 0.7
        v_score = 1.0 if color_range['v'][0] <= v <= color_range['v'][1] else 0.7
        
        return min(s_score, v_score)

    def adjust_for_shadows(self, color_info: ColorInfo, color_name: str) -> ColorInfo:
        """Adjust colors to account for shadows in light-colored garments"""
        # Check if this is a light-colored garment
        light_color_keywords = {'white', 'ivory', 'cream', 'off white', 'light', 'pale'}
        is_light_color = any(keyword in color_name.lower() for keyword in light_color_keywords)
        
        if is_light_color:
            h, s, v = self._rgb_to_hsv(color_info.rgb)
            
            # Adjust threshold for light colors - capture more of the white range
            if 50 < v < 98:  # Expanded range to catch more potential whites
                # Log original values
                logger.info(f"\nShadow Adjustment for {color_name}:")
                logger.info(f"Original - HSV: ({h:.1f}°, {s:.1f}%, {v:.1f}%), RGB: {color_info.rgb}, Hex: {color_info.hex}")
                
                # More aggressive boost for whites
                v_new = min(v * 1.25, 98)  # 25% boost for whites
                s_new = max(s * 0.75, 0)   # 25% reduction in saturation
                
                # Convert back to RGB
                bgr = cv2.cvtColor(np.uint8([[[h/2, s_new*2.55, v_new*2.55]]]), cv2.COLOR_HSV2BGR)[0][0]
                rgb = tuple(reversed(bgr))
                hex_code = '#{:02x}{:02x}{:02x}'.format(*rgb)
                
                # Log adjusted values
                logger.info(f"Adjusted - HSV: ({h:.1f}°, {s_new:.1f}%, {v_new:.1f}%), RGB: {rgb}, Hex: {hex_code}")
                
                return ColorInfo(
                    rgb=rgb,
                    lab=color_info.lab,
                    hex=hex_code,
                    hsv=(h, s_new, v_new),
                    frequency=color_info.frequency
                )
        
        return color_info

    def process_csv(self, input_data: Union[str, pd.DataFrame], output_path: str = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Process Matrixify CSV and create color metaobjects"""
        try:
            # Load data
            if isinstance(input_data, str):
                logger.info(f"Loading CSV from {input_data}")
                df = pd.read_csv(input_data)
            else:
                df = input_data.copy()
            
            # Initialize tracking
            metaobject_rows = []
            color_changes = []
            color_cache = {}  # Cache for color analysis results
            
            # Add a dictionary to track product colors
            product_colors = defaultdict(list)  # Key: product handle, Value: list of color handles
            
            # Get unique color-image combinations with product handle
            unique_colors = df[
                (df['Option1 Name'].str.lower() == 'color') & 
                (df['Variant Image'].notna())
            ][['Handle', 'Option1 Value', 'Variant Image']].drop_duplicates()  # Added Handle to selection
            
            total_colors = len(unique_colors)
            logger.info(f"Processing {total_colors} unique color variants")
            
            # Process each unique color-image combination
            for idx, row in unique_colors.iterrows():
                color_name = row['Option1 Value']
                image_url = row['Variant Image']
                product_handle = row['Handle'].split('/')[0]  # Get base product handle
                
                logger.info(f"Processing color {idx}/{len(unique_colors)}: {color_name} for product {product_handle}")
                
                # First create a temporary handle to use until we get the hex code
                temp_handle = color_name.lower().replace(' ', '-')
                
                local_image_path = self.download_image(image_url)
                if local_image_path:
                    try:
                        # Parse image and get mask
                        result = self.parser.parse_image(local_image_path)
                        mask = self.parser.get_garment_mask(result)
                        
                        # Modify the color extraction parameters for light colors
                        if 'white' in color_name.lower() or 'light' in color_name.lower():
                            self.color_extractor.background_threshold = 0.95  # Increase threshold for whites
                        else:
                            self.color_extractor.background_threshold = 0.85  # Default threshold
                        
                        # Extract initial colors
                        color_analysis = self.color_extractor.extract_colors(local_image_path, mask)
                        
                        # First adjust for shadows in light colors
                        adjusted_colors = [
                            self.adjust_for_shadows(color, color_name) 
                            for color in color_analysis['colors']
                        ]
                        
                        # Then apply confidence scoring to adjusted colors
                        weighted_colors = []
                        for color in adjusted_colors:
                            hsv = color.hsv  # Use HSV from adjusted colors
                            confidence = self.color_confidence_score(hsv, color_name)
                            
                            # Adjust color weight based on confidence
                            adjusted_frequency = color.frequency * confidence
                            weighted_colors.append(ColorInfo(
                                rgb=color.rgb,
                                lab=color.lab,
                                hex=color.hex,
                                hsv=hsv,
                                frequency=adjusted_frequency
                            ))
                        
                        # Sort and normalize frequencies
                        total_freq = sum(c.frequency for c in weighted_colors)
                        normalized_colors = [
                            ColorInfo(
                                rgb=c.rgb,
                                lab=c.lab,
                                hex=c.hex,
                                hsv=c.hsv,
                                frequency=(c.frequency/total_freq)*100
                            ) for c in weighted_colors
                        ]
                        
                        # Sort by adjusted frequency
                        normalized_colors.sort(key=lambda x: x.frequency, reverse=True)
                        
                        # Update color analysis with final weighted results
                        color_analysis['colors'] = normalized_colors
                        
                        # Get primary color hex from weighted analysis
                        primary_color = normalized_colors[0]
                        hex_code = primary_color.hex.lstrip('#')
                        
                        # Create proper handle format using weighted color
                        color_handle = f"{temp_handle}-{hex_code}"
                        
                        # Map to Shopify taxonomy color
                        taxonomy_color = self.map_to_shopify_color(color_name, hex_code)
                        
                        # Get color season analysis
                        garment_analysis = self.palette_classifier.classify_garment(
                            color_analysis['colors'],
                            primary_threshold=0.98,
                            secondary_threshold=0.90,
                            min_confidence=0.6,
                            pattern_threshold=0.02
                        )
                        season_results = self.palette_classifier.format_results(garment_analysis)
                        season_handles = self.get_season_handles(season_results)
                        
                        # Cache the results with season info
                        color_cache[color_name] = {
                            'handle': color_handle,
                            'hex_code': hex_code,
                            'taxonomy_color': taxonomy_color,
                            'color_season': season_handles
                        }
                        
                        # Create metaobject rows with proper handle
                        metaobject_rows.extend([
                            {
                                'Handle': color_handle,
                                'Command': 'MERGE',
                                'Definition: Handle': 'shopify--color-pattern',
                                'Definition: Name': 'Color',
                                'Field': 'label',
                                'Value': color_name
                            },
                            {
                                'Handle': color_handle,
                                'Command': 'MERGE',
                                'Definition: Handle': 'shopify--color-pattern',
                                'Definition: Name': 'Color',
                                'Field': 'color',
                                'Value': f"#{hex_code}"
                            },
                            {
                                'Handle': color_handle,
                                'Command': 'MERGE',
                                'Definition: Handle': 'shopify--color-pattern',
                                'Definition: Name': 'Color',
                                'Field': 'color_taxonomy_reference',
                                'Value': taxonomy_color
                            },
                            {
                                'Handle': color_handle,
                                'Command': 'MERGE',
                                'Definition: Handle': 'shopify--color-pattern',
                                'Definition: Name': 'Color',
                                'Field': 'pattern_taxonomy_reference',
                                'Value': 'gid://shopify/TaxonomyValue/2874'
                            }
                        ])
                        
                        # After successfully processing color, store the handle with its product
                        if color_handle:
                            product_colors[product_handle].append(f"shopify--color-pattern.{color_handle}")
                            logger.info(f"Added color {color_handle} to product {product_handle}")
                        
                    except Exception as e:
                        logger.error(f"Failed to process image {local_image_path}: {e}")
                        continue
                else:
                    logger.warning(f"Skipping color due to failed image download: {image_url}")
                    continue
            
            # After processing all colors, update the product rows
            for product_handle, color_handles in product_colors.items():
                # Get indices of all rows for this product
                product_indices = df[df['Handle'].str.startswith(f"{product_handle}/", na=False) | 
                                   (df['Handle'] == product_handle)].index
                
                if len(product_indices) > 0:
                    # Set all color handles in the first row
                    color_pattern_string = ', '.join(sorted(set(color_handles)))  # Remove duplicates and sort
                    df.loc[product_indices[0], 'Metafield: shopify.color-pattern [list.metaobject_reference]'] = color_pattern_string
                    
                    # Clear the field for other rows of the same product
                    if len(product_indices) > 1:
                        df.loc[product_indices[1:], 'Metafield: shopify.color-pattern [list.metaobject_reference]'] = ''
                    
                    logger.info(f"Set color patterns for {product_handle}: {color_pattern_string}")
            
            # Now set the color season metafields for each variant
            for _, variant in df.iterrows():
                if 'Option1 Name' in variant and variant['Option1 Name'].lower() == 'color':
                    color_name = variant['Option1 Value']
                    if color_name in color_cache:
                        cached = color_cache[color_name]
                        # Set color season metafield
                        df.loc[variant.name, 'Variant Metafield: custom.pallet [list.metaobject_reference]'] = cached['color_season']
                        
                        # Track change
                        color_changes.append({
                            'Handle': variant['Handle'],
                            'Variant': variant.name,
                            'Color': color_name,
                            'Hex': cached['hex_code'],
                            'Taxonomy': cached['taxonomy_color'],
                            'Season': cached['color_season']
                        })
            
            logger.info("Color processing complete")
            
            # Create metaobjects DataFrame
            metaobjects_df = pd.DataFrame(metaobject_rows)
            
            # Save files if output path provided
            if output_path:
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Save normalized products CSV
                df.to_csv(output_path, index=False)
                logger.info(f"Saved normalized products to {output_path}")
                
                # Save metaobjects to separate file
                metaobjects_path = output_dir / 'color_metaobjects.csv'
                metaobjects_df.to_csv(metaobjects_path, index=False)
                logger.info(f"Saved color metaobjects to {metaobjects_path}")
                
                # Save changes report
                changes_df = pd.DataFrame(color_changes)
                changes_path = output_dir / 'color_changes.csv'
                changes_df.to_csv(changes_path, index=False)
                logger.info(f"Saved color changes report to {changes_path}")
            
            return df, metaobjects_df
            
        except Exception as e:
            logger.error(f"Error in process_csv: {str(e)}", exc_info=True)
            raise

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

    def load_color_taxonomy(self) -> Dict[str, str]:
        """Load Shopify color taxonomy from file"""
        taxonomy_path = Path(__file__).parent.parent / 'data/Reference/shopify_color_taxonomy.txt'
        
        color_map = {}
        try:
            with open(taxonomy_path, 'r') as f:
                lines = f.readlines()
            
            # Process lines in pairs (color name followed by GID)
            for i in range(0, len(lines), 2):
                if i + 1 < len(lines):
                    color = lines[i].strip()
                    color_id = lines[i + 1].strip()
                    if color != 'Color':  # Skip header
                        color_map[color.lower()] = color_id
        
            logger.info(f"Loaded {len(color_map)} color taxonomy mappings")
            return color_map
        
        except FileNotFoundError:
            logger.warning(f"Color taxonomy file not found at {taxonomy_path}")
            logger.warning("Using default color mappings")
            
            # Return default mappings if file not found
            return {
                'white': 'gid://shopify/TaxonomyValue/3',
                'black': 'gid://shopify/TaxonomyValue/1',
                'blue': 'gid://shopify/TaxonomyValue/2',
                'bronze': 'gid://shopify/TaxonomyValue/657',
                'brown': 'gid://shopify/TaxonomyValue/7',
                'clear': 'gid://shopify/TaxonomyValue/17',
                'gold': 'gid://shopify/TaxonomyValue/4',
                'gray': 'gid://shopify/TaxonomyValue/8',
                'green': 'gid://shopify/TaxonomyValue/9',
                'multicolor': 'gid://shopify/TaxonomyValue/2865',
                'navy': 'gid://shopify/TaxonomyValue/15',
                'orange': 'gid://shopify/TaxonomyValue/10',
                'pink': 'gid://shopify/TaxonomyValue/11',
                'purple': 'gid://shopify/TaxonomyValue/12',
                'red': 'gid://shopify/TaxonomyValue/13',
                'rose gold': 'gid://shopify/TaxonomyValue/16',
                'silver': 'gid://shopify/TaxonomyValue/5',
                'white': 'gid://shopify/TaxonomyValue/3',
                'yellow': 'gid://shopify/TaxonomyValue/14'
            }

    def format_season_name(self, season_value: str) -> str:
        """Convert internal season value to display format"""
        season_mapping = {
            'SPRING_BRIGHT': 'Bright Spring',
            'SPRING_LIGHT': 'Light Spring',
            'SPRING_WARM': 'Warm Spring',
            'SUMMER_LIGHT': 'Light Summer',
            'SUMMER_SOFT': 'Soft Summer',
            'SUMMER_COOL': 'Cool Summer',
            'AUTUMN_WARM': 'Warm Autumn',
            'AUTUMN_SOFT': 'Soft Autumn',
            'AUTUMN_DEEP': 'Deep Autumn',
            'WINTER_BRIGHT': 'Bright Winter',
            'WINTER_COOL': 'Cool Winter',
            'WINTER_DEEP': 'Deep Winter'
        }
        return season_mapping.get(season_value, season_value)

    def format_season_handle(self, season_name: str) -> str:
        """Convert season name to handle format"""
        return f"pallet.{season_name.lower().replace(' ', '-')}"

    def get_season_handles(self, season_results: dict) -> str:
        """Get formatted handles for primary seasons only"""
        seasons = []
        
        # Only add primary seasons
        if season_results.get('primary_seasons'):
            for season in season_results['primary_seasons']:
                season_name = self.format_season_name(season.value)
                seasons.append(self.format_season_handle(season_name))
        
        # Raise error if no seasons found
        if not seasons:
            raise ValueError("No color seasons classified for this garment")
        
        # Return comma-separated list of handles
        return ', '.join(seasons)

    def analyze_brightness_distribution(self, image: np.ndarray, mask: np.ndarray) -> float:
        """Analyze brightness distribution to detect shadow bias"""
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        # Get value channel
        v = hsv[:, :, 2]
        # Get values only in mask
        masked_values = v[mask > 0]
        
        if len(masked_values) == 0:
            return 1.0
        
        # Calculate statistics
        median_v = np.median(masked_values)
        p90_v = np.percentile(masked_values, 90)
        
        # If there's a significant difference between median and 90th percentile,
        # this might indicate shadow presence
        shadow_factor = p90_v / median_v if median_v > 0 else 1.0
        return min(shadow_factor, 1.5)  # Cap the adjustment

def process_colors(input_file: str, output_dir: str):
    """Process colors in a Matrixify CSV file"""
    logger.info(f"Starting color processing for {input_file}")
    
    try:
        # Initialize components
        model_path = str(Path(__file__).parent.parent / 'models' / 'exp-schp-201908301523-atr.pth')
        
        # Validate model path exists
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model file not found at: {model_path}")
            
        logger.info("Initializing components...")
        parser = GarmentParser(
            model_path=model_path,
            dataset='atr',
            verbose=False  # Disable verbose output
        )
        color_extractor = ColorExtractor(n_colors=5, lab_threshold=20)
        palette_classifier = PaletteClassifier()
        normalizer = ColorNormalizer()
        
        # Process CSV
        logger.info("Processing CSV file...")
        products_df, metaobjects_df = normalizer.process_csv(
            input_file,
            output_path=Path(output_dir) / 'normalized_products.csv'
        )
        
        logger.info(f"Processed {len(products_df)} products")
        logger.info(f"Created {len(metaobjects_df)} color metaobjects")
        
        return products_df, metaobjects_df
        
    except Exception as e:
        logger.error(f"Error processing colors: {str(e)}", exc_info=True)
        raise 