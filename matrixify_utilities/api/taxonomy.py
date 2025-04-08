import base64
import json
from typing import Dict, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class TaxonomyHelper:
    def __init__(self):
        self.taxonomy_cache = {}  # Cache for encoded IDs
        self.mappings = self._load_mappings()
    
    def _load_mappings(self) -> List[Dict]:
        """Load taxonomy mappings from JSON file"""
        try:
            mappings_file = Path(__file__).parent.parent / 'data' / 'all_mappings.json'
            logger.debug(f"Looking for mappings file at: {mappings_file.absolute()}")
            
            if not mappings_file.exists():
                logger.error(f"Mappings file not found at: {mappings_file.absolute()}")
                # List contents of parent directories
                data_dir = mappings_file.parent
                logger.error(f"Contents of {data_dir}:")
                for f in data_dir.glob('*'):
                    logger.error(f"  {f.name}")
                
                parent_dir = data_dir.parent
                logger.error(f"Contents of {parent_dir}:")
                for f in parent_dir.glob('*'):
                    logger.error(f"  {f.name}")
                return []
            
            logger.debug(f"Found mappings file, size: {mappings_file.stat().st_size} bytes")
            
            with open(mappings_file, 'r') as f:
                data = json.load(f)
                logger.debug(f"Successfully loaded JSON data")
                logger.debug(f"Keys in data: {list(data.keys())}")
                
                rules = data.get('mappings', [{}])[0].get('rules', [])
                logger.debug(f"Loaded {len(rules)} rules")
                
                # Print first few rules to verify structure
                logger.debug("\nFirst few rules:")
                for rule in rules[:3]:
                    input_cat = rule.get('input', {}).get('category', {})
                    logger.debug(f"Rule: {input_cat.get('full_name')} (ID: {input_cat.get('id')})")
                
                # Print rules containing "Dresses"
                dress_rules = [r for r in rules 
                             if 'Dresses' in r.get('input', {}).get('category', {}).get('full_name', '')]
                
                logger.debug(f"\nFound {len(dress_rules)} rules containing 'Dresses'")
                for rule in dress_rules:
                    input_cat = rule.get('input', {}).get('category', {})
                    logger.debug(f"Dress rule: {input_cat.get('full_name')} (ID: {input_cat.get('id')})")
                
                return rules
        except Exception as e:
            logger.error(f"Failed to load taxonomy mappings: {e}")
            logger.error(f"Current directory: {Path.cwd()}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def get_category_by_numeric_id(self, numeric_id: str) -> Optional[Dict]:
        """Find category details using numeric ID (e.g., '160')"""
        try:
            for rule in self.mappings:
                input_cat = rule.get('input', {}).get('category', {})
                output_cat = rule.get('output', {}).get('category', [{}])[0]
                if output_cat.get('id') == numeric_id:
                    return {
                        'numeric_id': numeric_id,
                        'taxonomy_id': input_cat['id'],
                        'full_name': input_cat['full_name']
                    }
        except Exception as e:
            logger.error(f"Error in get_category_by_numeric_id: {e}")
        return None

    def get_category_by_name(self, category_name: str) -> Optional[Dict]:
        """Find category details using name (e.g., 'Dresses')"""
        try:
            logger.debug(f"\nSearching for category: {category_name}")
            
            # Debug the mappings structure
            logger.debug("Mappings structure:")
            logger.debug(json.dumps(self.mappings[0], indent=2))
            
            # Get the rules
            rules = self.mappings
            logger.debug(f"Found {len(rules)} rules to check")
            
            # Search through rules
            for rule in rules:
                # Get the categories
                input_cat = rule.get('input', {}).get('category', {})
                output_cats = rule.get('output', {}).get('category', [])
                
                # Get the full names and IDs
                input_name = input_cat.get('full_name', '')
                input_id = input_cat.get('id', '')
                
                # Debug every rule we check
                logger.debug("\nChecking rule:")
                logger.debug(f"Full name: {input_name}")
                logger.debug(f"ID: {input_id}")
                
                # Split the full name into parts
                name_parts = input_name.split(' > ')
                last_part = name_parts[-1] if name_parts else ''
                
                logger.debug(f"Last part: {last_part}")
                logger.debug(f"Category name: {category_name}")
                logger.debug(f"Match? {last_part == category_name}")
                
                # Check if this is a matching category
                if last_part == category_name:
                    logger.debug("\nFound matching category:")
                    logger.debug(f"Input category: {input_cat}")
                    logger.debug(f"Output categories: {output_cats}")
                    logger.debug("Full rule:")
                    logger.debug(json.dumps(rule, indent=2))
                    
                    # Get the output ID
                    output_id = output_cats[0].get('id', '') if output_cats else ''
                    
                    # Print ID details
                    logger.debug("\nID details:")
                    logger.debug(f"Input ID: {input_id} ({type(input_id)})")
                    logger.debug(f"Output ID: {output_id} ({type(output_id)})")
                    
                    # Check if this is ID 160
                    if str(input_id) == "160":
                        logger.debug("\nFound exact match with ID 160!")
                        return {
                            'taxonomy_id': input_id,    # Use numeric ID from input
                            'shopify_id': output_id,    # Use Shopify ID from output
                            'full_name': input_name
                        }
                    else:
                        logger.debug(f"Skipping rule - not ID 160 (got {input_id})")
            
            logger.debug("\nNo matching category found!")
            return None
        
        except Exception as e:
            logger.error(f"Error in get_category_by_name: {e}")
            return None

    def get_taxonomy_gid(self, identifier: str) -> Optional[str]:
        """Get taxonomy GID using either numeric ID or name"""
        # Check cache first
        if identifier in self.taxonomy_cache:
            return self.taxonomy_cache[identifier]

        # Try finding by numeric ID first
        category = self.get_category_by_numeric_id(identifier)
        if not category:
            # Try finding by name
            category = self.get_category_by_name(identifier)
        
        if category:
            self.taxonomy_cache[identifier] = category['taxonomy_id']
            return category['taxonomy_id']
        
        logger.error(f"Could not find taxonomy ID for: {identifier}")
        return None

    def list_categories(self) -> List[Dict]:
        """List all available categories with their mappings"""
        categories = []
        try:
            for rule in self.mappings:
                input_cat = rule.get('input', {}).get('category', {})
                output_cat = rule.get('output', {}).get('category', [{}])[0]
                if input_cat and output_cat:
                    categories.append({
                        'numeric_id': output_cat.get('id'),
                        'taxonomy_id': input_cat.get('id'),
                        'full_name': input_cat.get('full_name')
                    })
        except Exception as e:
            logger.error(f"Error in list_categories: {e}")
        return categories 

    def get_category_by_taxonomy_id(self, taxonomy_id: str) -> Optional[Dict]:
        """Find category details using taxonomy ID (e.g., 'aa-1-4')"""
        try:
            for rule in self.mappings:
                input_cat = rule.get('input', {}).get('category', {})
                output_cat = rule.get('output', {}).get('category', [{}])[0]
                if input_cat.get('id', '').endswith(taxonomy_id):
                    return {
                        'numeric_id': output_cat['id'],
                        'taxonomy_id': input_cat['id'],
                        'full_name': input_cat['full_name']
                    }
        except Exception as e:
            logger.error(f"Error in get_category_by_taxonomy_id: {e}")
        return None 