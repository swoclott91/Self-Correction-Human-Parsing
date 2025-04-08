import json
import requests
from pathlib import Path
from typing import Dict, Optional, List
import logging
import re
from ..api.client import ShopifyClient

logger = logging.getLogger(__name__)

class TaxonomyMapper:
    """Maps between different taxonomy formats using Shopify's official taxonomy"""
    
    GITHUB_BASE_URL = "https://raw.githubusercontent.com/Shopify/product-taxonomy/main/dist/en"
    
    def __init__(self):
        self.client = ShopifyClient()
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.taxonomy_file = self.data_dir / 'categories.json'
        self.taxonomy_cache = {}
        self.path_to_id = {}
        self.id_to_path = {}
        
        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load initial taxonomy
        self.update_taxonomy()
        
    def update_taxonomy(self, force=False) -> Dict:
        """Update taxonomy data from GitHub"""
        if not force and self.taxonomy_file.exists():
            try:
                with open(self.taxonomy_file) as f:
                    self.taxonomy_cache = json.load(f)
                    if isinstance(self.taxonomy_cache, dict):
                        logger.info(f"Loaded {len(self.taxonomy_cache)} categories from cache")
                        self.build_category_maps()
                        return self.taxonomy_cache
                    else:
                        logger.error("Invalid cache format")
            except Exception as e:
                logger.error(f"Error loading taxonomy cache: {e}")

        # Download fresh taxonomy
        logger.info("Downloading fresh taxonomy from GitHub...")
        try:
            # Download categories.json instead of .txt for better structure
            response = requests.get(f"{self.GITHUB_BASE_URL}/categories.json")
            response.raise_for_status()
            
            raw_categories = response.json()
            
            # Process the categories
            self.taxonomy_cache = {}
            
            def process_category(category):
                """Recursively process category and its children"""
                category_id = category['id']
                self.taxonomy_cache[category_id] = {
                    'name': category['name'],
                    'fullName': category['full_path'],
                    'level': len(category['full_path'].split('>')),
                    'parent_id': category.get('parent_id')
                }
                
                # Process children if they exist
                for child in category.get('children', []):
                    process_category(child)
            
            # Process all categories
            for category in raw_categories:
                process_category(category)
            
            # Save to cache file
            with open(self.taxonomy_file, 'w') as f:
                json.dump(self.taxonomy_cache, f, indent=2)
            
            logger.info(f"Downloaded {len(self.taxonomy_cache)} categories")
            self.build_category_maps()
            return self.taxonomy_cache
            
        except Exception as e:
            error_msg = f"Failed to download taxonomy from GitHub: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def build_category_maps(self):
        """Build path-to-id and id-to-path mappings"""
        self.path_to_id = {}
        self.id_to_path = {}
        
        for category_id, details in self.taxonomy_cache.items():
            if details.get('fullName'):
                # Store both the full path and the normalized version
                full_path = details['fullName'].strip()
                self.path_to_id[full_path] = category_id
                self.id_to_path[category_id] = full_path
                
                # Also store without spaces around '>'
                normalized_path = ' > '.join(p.strip() for p in full_path.split('>'))
                if normalized_path != full_path:
                    self.path_to_id[normalized_path] = category_id
    
    def get_category_id(self, category_path: str) -> Optional[str]:
        """Get category ID from path"""
        if not category_path:
            return None
            
        # Clean input
        category_path = category_path.strip()
        
        # Try exact match
        if category_path in self.path_to_id:
            return self.path_to_id[category_path]
        
        # If path contains subcategories we don't support (like Mini Dresses),
        # try to find the parent category (Dresses)
        parts = category_path.split(' > ')
        while len(parts) > 1:
            parent_path = ' > '.join(parts[:-1])
            if parent_path in self.path_to_id:
                logger.info(f"Using parent category '{parent_path}' instead of '{category_path}'")
                return self.path_to_id[parent_path]
            parts.pop()
        
        # Try normalized version
        normalized_path = ' > '.join(p.strip() for p in category_path.split('>'))
        if normalized_path in self.path_to_id:
            return self.path_to_id[normalized_path]
        
        logger.warning(f"No category ID found for: {category_path}")
        return None
    
    def get_category_path(self, category_id: str) -> Optional[str]:
        """Get category path from ID"""
        if not category_id:
            return None
            
        # Clean input
        category_id = category_id.strip()
        
        return self.id_to_path.get(category_id)
    
    def list_categories(self, parent_path: str = None) -> List[str]:
        """List subcategories of a given category"""
        categories = []
        parent_id = self.get_category_id(parent_path) if parent_path else None
        
        for cat_id, details in self.taxonomy_cache.items():
            if (parent_id and details.get('parent_id') == parent_id) or (not parent_id and details.get('level') == 1):
                categories.append(details['fullName'])
                
        return sorted(categories)

    def debug_available_categories(self):
        """Print available categories for debugging"""
        logger.info("\nAvailable Categories:")
        for name, details in self.taxonomy_cache.items():
            logger.info(f"  {name}")
            logger.info(f"  ID: {details['id']}\n")

    def _process_taxonomy_node(self, node: Dict, parent_id: str = None):
        """Recursively process taxonomy nodes"""
        node_id = node['id']
        self.taxonomy_cache[node_id] = {
            'name': node['name'],
            'fullName': node['fullName'],
            'parent_id': parent_id
        }
        
        # Process children if they exist
        for child_level in ['children']:
            if child_level in node and 'nodes' in node[child_level]:
                for child in node[child_level]['nodes']:
                    self._process_taxonomy_node(child, node_id)
                    # Recurse through deeper levels
                    if 'children' in child and 'nodes' in child['children']:
                        for grandchild in child['children']['nodes']:
                            self._process_taxonomy_node(grandchild, child['id'])
                            if 'children' in grandchild and 'nodes' in grandchild['children']:
                                for great_grandchild in grandchild['children']['nodes']:
                                    self._process_taxonomy_node(great_grandchild, grandchild['id'])

    def get_standard_category(self, category_path: str) -> Optional[str]:
        """Map our category path to Shopify's standard taxonomy"""
        if not category_path:
            return None
        
        # If it's a dress subcategory, return the standard Dresses category
        if 'Dresses' in category_path:
            return 'Apparel & Accessories > Clothing > Dresses'
        
        # Handle other mappings as needed
        if 'Tops' in category_path or 'Blouses' in category_path:
            return 'Apparel & Accessories > Clothing > Clothing Tops > Blouses'
        
        return category_path
        
    def normalize_category_name(self, name: str) -> str:
        """Normalize category name for comparison"""
        if not name:
            return ''
        # Remove special chars, convert to lowercase
        normalized = re.sub(r'[^\w\s]', '', name.lower())
        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        logger.debug(f"Normalized '{name}' to '{normalized}'")
        return normalized

    def load_taxonomy(self):
        """Load taxonomy mappings from file"""
        logger.info("Loading taxonomy mappings...")
        # Add debug logging
        logger.debug("Current taxonomy mappings:")
        for category, details in self.taxonomy_cache.items():
            logger.debug(f"  {category} -> {details}")
            
    def load_category_mappings():
        """Load category mappings from Shopify"""
        categories = {
            'Apparel & Accessories > Clothing > Dresses': 'gid://shopify/TaxonomyCategory/aa-1-4',
            'Apparel & Accessories > Clothing > Clothing Tops > Blouses': 'gid://shopify/TaxonomyCategory/aa-1-13-1',
        }
        return categories 