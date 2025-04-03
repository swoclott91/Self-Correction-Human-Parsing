import pandas as pd
import logging
from pathlib import Path
from typing import Union, Dict, List, Tuple
import re
from collections import defaultdict
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

class CategoryNormalizer:
    def __init__(self):
        self.unrecognized_categories = defaultdict(int)
        self.category_stats = defaultdict(int)
        
        # Load category mappings
        self.category_mapping = load_category_mappings()
        
        # Build valid paths and levels
        self.valid_paths = set()
        self.valid_levels = defaultdict(set)
        
        for path, info in self.category_mapping.items():
            self.valid_paths.add(path)
            parts = path.split(' > ')
            for i, part in enumerate(parts, 1):
                self.valid_levels[i].add(part)
        
        # Build regex patterns for category matching
        self.category_patterns = {
            # Base patterns
            r'(?i)^apparel$': 'Apparel & Accessories',
            r'(?i)^clothing$': 'Apparel & Accessories > Clothing',
            
            # Specific category patterns
            r'(?i)^tops?$': 'Apparel & Accessories > Clothing > Clothing Tops',
            r'(?i)^dresses?$': 'Apparel & Accessories > Clothing > Dresses',
            r'(?i)^pants?$': 'Apparel & Accessories > Clothing > Pants',
            r'(?i)^shorts?$': 'Apparel & Accessories > Clothing > Shorts',
            r'(?i)^skirts?$': 'Apparel & Accessories > Clothing > Skirts',
            r'(?i)^outerwear$': 'Apparel & Accessories > Clothing > Outerwear',
            r'(?i)^one[\s-]pieces?$': 'Apparel & Accessories > Clothing > One-Pieces',
            r'(?i)^sets?$': 'Apparel & Accessories > Clothing > Outfit Sets',
            
            # Add patterns for all valid paths
            **{rf'(?i)^{re.escape(info["name"])}$': path 
               for path, info in self.category_mapping.items()}
        }

    def validate_category_path(self, category: str) -> bool:
        """Validate that a category path follows the correct hierarchy"""
        if not category:
            return False
            
        parts = category.split(' > ')
        
        # Check number of levels
        if len(parts) > 4:
            logger.warning(f"Invalid category depth: {category}")
            return False
            
        # Validate each level
        for level, part in enumerate(parts, 1):
            if part not in self.valid_levels[level]:
                logger.warning(f"Invalid category at level {level}: {part}")
                return False
                
        return True

    def normalize_category(self, category: str) -> str:
        """Normalize a category string to standard Shopify taxonomy"""
        # Handle empty or non-string categories
        if pd.isna(category) or not category:
            return ''
        
        # Convert to string if needed
        if not isinstance(category, str):
            category = str(category)
        
        category = category.strip()
        original_category = category
        
        # Check if already a valid path
        if category in self.valid_paths:
            self.category_stats[category] += 1
            return category
        
        # Try each mapping pattern
        for pattern, replacement in self.category_patterns.items():
            if re.search(pattern, category, re.IGNORECASE):
                self.category_stats[replacement] += 1
                return replacement
        
        # Track unrecognized category
        self.unrecognized_categories[original_category] += 1
        logger.warning(f"No mapping found for category: {category}")
        return category

    def generate_category_report(self) -> Dict:
        """Generate report of category normalization statistics"""
        return {
            'unrecognized_categories': dict(self.unrecognized_categories),
            'category_stats': dict(self.category_stats),
            'total_processed': sum(self.category_stats.values()),
            'total_unrecognized': sum(self.unrecognized_categories.values())
        }

    def infer_category_from_title(self, title: str) -> str:
        """Infer category from product title using YAML reference data"""
        title = title.lower()
        
        # First check for primary garment types - these take priority
        if any(x in title for x in ['sweater', 'cardigan']):
            return 'Apparel & Accessories > Clothing > Clothing Tops > Sweaters'
        elif any(x in title for x in ['hoodie', 'sweatshirt']):
            return 'Apparel & Accessories > Clothing > Clothing Tops > Hoodies'
        elif any(x in title for x in ['blouse']):
            return 'Apparel & Accessories > Clothing > Clothing Tops > Blouses'
        
        # Then check for sets
        if any(x in title for x in ['set', 'coordinate', 'matching', ' & ', ' and ']):
            # Verify it's a clothing set by checking for multiple pieces
            has_top = any(x in title for x in ['top', 'shirt', 'tank'])
            has_bottom = any(x in title for x in ['pant', 'short', 'skirt', 'bottom', 'legging'])
            if has_top and has_bottom:
                return 'Apparel & Accessories > Clothing > Outfit Sets'
            elif any(x in title for x in ['activewear', 'sport', 'athletic']):
                return 'Apparel & Accessories > Clothing > Activewear'
            elif any(x in title for x in ['sleep', 'pajama', 'pj']):
                return 'Apparel & Accessories > Clothing > Sleepwear'
        
        # Check for one-pieces
        if any(x in title for x in ['overall', 'jumpsuit', 'romper', 'playsuit']):
            return 'Apparel & Accessories > Clothing > One-Pieces'
        elif 'dress' in title:
            if 'maxi' in title:
                return 'Apparel & Accessories > Clothing > Dresses > Maxi Dresses'
            elif 'mini' in title:
                return 'Apparel & Accessories > Clothing > Dresses > Mini Dresses'
            elif 'midi' in title:
                return 'Apparel & Accessories > Clothing > Dresses > Midi Dresses'
            return 'Apparel & Accessories > Clothing > Dresses'
        
        # Check for other tops
        if any(x in title for x in ['tank']):
            return 'Apparel & Accessories > Clothing > Clothing Tops > Tank Tops'
        elif any(x in title for x in ['crop', 'cropped']):
            return 'Apparel & Accessories > Clothing > Clothing Tops > Crop Tops'
        elif any(x in title for x in ['top', 'shirt']):
            return 'Apparel & Accessories > Clothing > Clothing Tops'
        
        # Check for bottoms
        if any(x in title for x in ['jean']):
            return 'Apparel & Accessories > Clothing > Pants > Jeans'
        elif any(x in title for x in ['legging']):
            return 'Apparel & Accessories > Clothing > Pants > Leggings'
        elif any(x in title for x in ['wide leg']):
            return 'Apparel & Accessories > Clothing > Pants > Wide Leg Pants'
        elif any(x in title for x in ['pant', 'trouser']):
            return 'Apparel & Accessories > Clothing > Pants'
        elif 'skirt' in title:
            if 'mini' in title:
                return 'Apparel & Accessories > Clothing > Skirts > Mini Skirts'
            elif 'midi' in title:
                return 'Apparel & Accessories > Clothing > Skirts > Midi Skirts'
            elif 'maxi' in title:
                return 'Apparel & Accessories > Clothing > Skirts > Maxi Skirts'
            return 'Apparel & Accessories > Clothing > Skirts'
        elif 'short' in title:
            return 'Apparel & Accessories > Clothing > Shorts'
        
        # Check for outerwear
        if any(x in title for x in ['jacket']):
            return 'Apparel & Accessories > Clothing > Outerwear > Jackets'
        elif any(x in title for x in ['coat']):
            return 'Apparel & Accessories > Clothing > Outerwear > Coats'
        elif any(x in title for x in ['blazer']):
            return 'Apparel & Accessories > Clothing > Outerwear > Blazers'
        
        # Check other patterns using reference data
        for path, info in self.category_mapping.items():
            if info['name'].lower() in title:
                return path
        
        # Default category
        return 'Apparel & Accessories > Clothing'

def load_category_mappings():
    """Load category mappings from YAML reference file"""
    yaml_path = Path(__file__).parent.parent / 'data/Reference/aa_apparel_accessories.yaml'
    
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    
    # Build category mapping
    category_mapping = {}
    
    def process_node(node, parent_path=''):
        """Recursively process nodes to build category paths"""
        current_path = f"{parent_path} > {node['name']}" if parent_path else node['name']
        
        # Add mapping for this node
        category_mapping[current_path] = {
            'id': node['id'],
            'name': node['name'],
            'attributes': node.get('attributes', [])
        }
        
        # Process children
        for child_id in node.get('children', []):
            child_node = next(
                (item for item in data if item['id'] == child_id), 
                None
            )
            if child_node:
                process_node(child_node, current_path)
    
    # Process from root
    root_nodes = [node for node in data if len(node['id'].split('-')) == 1]
    for node in root_nodes:
        process_node(node)
    
    return category_mapping

def process_csv(input_data: Union[str, pd.DataFrame], output_path: str = None) -> Tuple[pd.DataFrame, Dict]:
    """Process Matrixify CSV and normalize categories"""
    
    # Load category mappings from YAML
    category_mapping = load_category_mappings()
    
    # Load data
    if isinstance(input_data, str):
        df = pd.read_csv(input_data)
    else:
        df = input_data.copy()
    
    logger.info("Processing category normalization")
    
    # Initialize normalizer
    normalizer = CategoryNormalizer()
    
    # Track changes for reporting
    changes = []
    unrecognized = defaultdict(int)
    
    # Process unique products
    unique_products = df.drop_duplicates('Handle')[['Handle', 'Title', 'Category']]
    
    for _, row in unique_products.iterrows():
        handle = row['Handle']
        title = row['Title']
        original_category = row['Category']
        
        # Try to infer category from title if missing
        if pd.isna(original_category):
            inferred_category = normalizer.infer_category_from_title(title)
            logger.info(f"Inferred category '{inferred_category}' for product '{title}'")
            
            # Update all variants for this product
            mask = df['Handle'] == handle
            
            # Update all category fields consistently
            if inferred_category in category_mapping:
                mapping = category_mapping[inferred_category]
                df.loc[mask, 'Category'] = inferred_category
                df.loc[mask, 'Category: ID'] = mapping['id']
                df.loc[mask, 'Category: Name'] = mapping['name']
            
            changes.append({
                'Handle': handle,
                'Title': title,
                'Old Category': 'Not Set',
                'New Category': inferred_category,
                'Change Type': 'Inferred'
            })
            
            original_category = inferred_category
        
        # Normalize category
        if original_category:
            normalized_category = normalizer.normalize_category(original_category)
            
            if normalized_category and normalized_category != original_category:
                # Update all variants
                mask = df['Handle'] == handle
                
                # Update all category fields consistently
                if normalized_category in category_mapping:
                    mapping = category_mapping[normalized_category]
                    df.loc[mask, 'Category'] = normalized_category
                    df.loc[mask, 'Category: ID'] = mapping['id']
                    df.loc[mask, 'Category: Name'] = mapping['name']
                
                changes.append({
                    'Handle': handle,
                    'Title': title,
                    'Old Category': original_category,
                    'New Category': normalized_category,
                    'Change Type': 'Normalized'
                })
            elif normalized_category != original_category:
                unrecognized[original_category] += 1
    
    # Ensure Command field is set to MERGE
    if 'Command' in df.columns:
        df['Command'] = 'MERGE'
    
    # Save reports
    if output_path:
        report_dir = Path(output_path).parent / 'reports'
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # Save changes report
        if changes:
            changes_df = pd.DataFrame(changes)
            changes_path = report_dir / 'category_normalization_changes.csv'
            changes_df.to_csv(changes_path, index=False)
            logger.info(f"Saved changes report to {changes_path}")
    
        # Save category statistics
        stats_df = pd.DataFrame([
            {'Category': cat, 'Count': count} 
            for cat, count in normalizer.category_stats.items()
        ])
        stats_df.to_csv(report_dir / 'category_statistics.csv', index=False)
        logger.info(f"Saved category statistics to {report_dir / 'category_statistics.csv'}")
    
    # Save normalized CSV
    if output_path:
        df.to_csv(output_path, index=False)
        logger.info(f"Saved normalized CSV to {output_path}")
    
    return df, {
        'changes': changes,
        'unrecognized': dict(unrecognized),
        'category_stats': normalizer.category_stats
    }

def get_category_id(category_path: str) -> str:
    """Map category path to Shopify taxonomy ID"""
    # This is a placeholder - you'll need to implement the actual mapping
    category_id_map = {
        'Apparel & Accessories > Clothing > Clothing Tops': 'aa-1-13',
        'Apparel & Accessories > Clothing > Outfit Sets': 'aa-1-14',
        'Apparel & Accessories > Clothing > One-Pieces': 'aa-1-15',
        'Apparel & Accessories > Clothing > Outerwear': 'aa-1-16',
        # Add more mappings as needed
    }
    return category_id_map.get(category_path, '') 