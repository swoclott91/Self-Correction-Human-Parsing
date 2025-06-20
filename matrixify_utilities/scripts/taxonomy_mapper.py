import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class TaxonomyMapper:
    """Maps between Shopify category paths and GIDs, provides attribute validation"""
    
    def __init__(self, taxonomy_dir: Optional[Path] = None):
        """Initialize with taxonomy directory"""
        self.taxonomy_dir = taxonomy_dir or Path(__file__).parent.parent / 'taxonomy_data'
        
        # Load categories
        categories_file = self.taxonomy_dir / 'categories.json'
        with open(categories_file) as f:
            categories_data = json.load(f)
            self.categories = categories_data.get('data', {})
        
        # Load values
        values_file = self.taxonomy_dir / 'values.json'
        with open(values_file) as f:
            values_data = json.load(f)
            # Add debug logging
            logger.debug(f"Values file structure: {list(values_data.keys())}")
            logger.debug(f"Sample values: {list(values_data.get('data', {}).keys())[:5]}")
            self.values = values_data.get('data', {})
        
        # Load attributes from apparel_accessories_attributes.json
        attributes_file = self.taxonomy_dir / 'apparel_accessories_attributes.json'
        with open(attributes_file) as f:
            attributes_data = json.load(f)
            # Build attributes dict from verticals data
            self.attributes = {}
            for vertical in attributes_data.get("verticals", []):
                if vertical["name"] == "Apparel & Accessories":
                    for category in vertical.get("categories", []):
                        for attr in category.get("attributes", []):
                            attr_id = attr.get("id")
                            if attr_id:
                                self.attributes[attr_id] = {
                                    "handle": attr.get("handle"),
                                    "name": attr.get("name"),
                                    "description": attr.get("description")
                                }
        
        # Load GID cache
        cache_path = Path(__file__).parent.parent / 'metaobject_sync/gid_cache.json'
        logger.debug(f"Loading GID cache from: {cache_path}")
        try:
            with open(cache_path) as f:
                self.gid_cache = json.load(f)
                logger.debug(f"Loaded {len(self.gid_cache)} cache entries")
        except Exception as e:
            logger.error(f"Failed to load GID cache: {e}")
            self.gid_cache = {}
        
        # Build path -> GID mapping
        self.path_to_gid: Dict[str, str] = {}
        self.gid_to_path: Dict[str, str] = {}
        self._build_path_mappings()
        
        # Cache allowed attributes per category
        self.category_attributes: Dict[str, Set[str]] = {}
        self._build_attribute_mappings()

        # Build reverse lookups
        self.handle_to_attribute_id = {
            attr_data["handle"]: attr_id 
            for attr_id, attr_data in self.attributes.items()
        }
        
        logger.debug(f"Loaded {len(self.categories)} categories")
        logger.debug(f"Loaded {len(self.attributes)} attributes")
        logger.debug(f"Loaded {len(self.values)} values")

    def _load_json(self, filename: str) -> Dict:
        """Load and parse a JSON file from the taxonomy directory"""
        try:
            with open(self.taxonomy_dir / filename) as f:
                data = json.load(f)
                return data.get('data', {})
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load {filename}: {e}")
            return {}

    def _build_path_mappings(self) -> None:
        """Build bidirectional mappings between category paths and GIDs"""
        for gid, category in self.categories.items():
            path = category.get('path')
            if path:
                self.path_to_gid[path] = gid
                self.gid_to_path[gid] = path
                
                # Also map without "Apparel & Accessories >" prefix for convenience
                if path.startswith("Apparel & Accessories > "):
                    short_path = path.replace("Apparel & Accessories > ", "")
                    self.path_to_gid[short_path] = gid

    def _build_attribute_mappings(self) -> None:
        """Build mapping of category GIDs to their allowed attributes"""
        for gid, category in self.categories.items():
            allowed_attrs = set(category.get('allowed_attributes', []))
            self.category_attributes[gid] = allowed_attrs

    def get_category_id_from_path(self, path: str) -> Optional[str]:
        """Get category GID from path"""
        # Normalize path
        path = path.strip().lower()
        
        # Search through categories
        for category_id, info in self.categories.items():
            category_path = info.get('path', '')
            if category_path.lower() == path:
                logger.debug(f"Found category {category_id} for path: {path}")
                return category_id
            
        # Try with "Apparel & Accessories >" prefix if not found
        if not path.startswith("apparel & accessories > "):
            prefixed_path = f"Apparel & Accessories > {path}"
            for category_id, info in self.categories.items():
                category_path = info.get('path', '')
                if category_path.lower() == prefixed_path.lower():
                    logger.debug(f"Found category {category_id} for path with prefix: {prefixed_path}")
                    return category_id
            
        logger.warning(f"No category found for path: {path}")
        return None

    def get_path_from_category_id(self, category_id: str) -> Optional[str]:
        """Get category path from GID"""
        category_info = self.categories.get(category_id, {})
        return category_info.get('path')

    def get_allowed_attribute_ids(self, category_gid: str) -> 'set[str]':
        """Get set of allowed attribute GIDs for a category"""
        # Use cached mapping if available
        if category_gid in self.category_attributes:
            return self.category_attributes[category_gid]
        
        # Otherwise build from category data
        category = self.categories.get(category_gid, {})
        allowed = set(category.get('allowed_attributes', []))
        
        # Cache for future use
        self.category_attributes[category_gid] = allowed
        
        logger.debug(f"Category {category_gid} allows {len(allowed)} attributes")
        return allowed

    def get_attribute_info(self, attribute_id: str) -> Optional[Dict]:
        """Get attribute details including name, type, and allowed values"""
        info = self.attributes.get(attribute_id)
        if not info:
            logger.warning(f"No info found for attribute {attribute_id}")
        return info

    def get_valid_values_for_attribute(self, attr_id: str) -> Dict[str, Dict]:
        """Get valid values for an attribute from the taxonomy"""
        # Use cached mapping if available
        if not hasattr(self, 'attribute_values'):
            self.attribute_values = {}
            for value_id, value_info in self.values.items():
                attribute_id = value_info.get('attribute_id')
                if attribute_id:
                    if attribute_id not in self.attribute_values:
                        self.attribute_values[attribute_id] = {}
                    self.attribute_values[attribute_id][value_id] = value_info
        
        valid_values = self.attribute_values.get(attr_id, {})
        
        if not valid_values:
            logger.debug(f"No valid values found for attribute {attr_id}")
        else:
            logger.debug(f"Found {len(valid_values)} valid values for attribute {attr_id}")
        
        return valid_values

    def get_value_info(self, value_id: str) -> Optional[Dict]:
        """Get value details including name and metadata"""
        return self.values.get(value_id)

    def is_valid_attribute_for_category(self, category_id: str, attribute_id: str) -> bool:
        """Check if an attribute is valid for a category"""
        allowed = self.get_allowed_attribute_ids(category_id)
        return attribute_id in allowed

    def get_apparel_categories(self) -> List[Dict]:
        """Get all categories under Apparel & Accessories"""
        apparel_categories = []
        for gid, category in self.categories.items():
            if category['path'].startswith("Apparel & Accessories"):
                apparel_categories.append({
                    'gid': gid,
                    'path': category['path'],
                    'name': category['name'],
                    'level': category['level']
                })
        return apparel_categories

    def format_graphql_input(self, product_id: str, category_id: str, attributes: Dict[str, Union[str, List[str]]]) -> Dict:
        """Format product data for GraphQL mutation"""
        if category_id not in self.categories:
            raise ValueError(f"Invalid category ID: {category_id}")
        
        allowed_attrs = self.get_allowed_attribute_ids(category_id)
        metafields = []
        
        for attr_id, values in attributes.items():
            # Skip category info dict
            if attr_id == 'category':
                continue
            
            if attr_id not in allowed_attrs:
                logger.debug(f"Attribute {attr_id} not allowed for category {category_id}")
                continue
            
            attr_info = self.attributes.get(attr_id, {})
            if not attr_info:
                continue

            # Convert single values to list if needed
            if not isinstance(values, list):
                values = [values]
            
            # Remove any array notation from the values
            cleaned_values = []
            for value in values:
                if isinstance(value, str):
                    # Remove any ["..."] wrapping
                    value = value.strip('[]" ')
                if value in self.values:  # Validate value exists
                    cleaned_values.append(value)
            
            if cleaned_values:
                metafields.append({
                    "namespace": "shopify",
                    "key": attr_info.get('handle', ''),
                    "value": json.dumps(cleaned_values) if len(cleaned_values) > 1 else cleaned_values[0],
                    "type": "list.metaobject_reference" if len(cleaned_values) > 1 else "metaobject_reference"
                })
        
        return {
            "id": product_id,
            "category": category_id,
            "metafields": metafields
        }

    def get_paths_by_category_name(self, name: str, text: str = "") -> List[str]:
        """
        Return all full paths that match a category name (case-insensitive)
        Args:
            name: Category name to match
            text: Optional product text to help disambiguate
        """
        matches = []
        name_lower = name.lower()
        text_lower = text.lower()
        
        logger.debug(f"Looking for paths matching category: {name}")
        
        # Map common category names to their full paths
        CATEGORY_MAP = {
            "Tops": ["Clothing > Clothing Tops", "Clothing > Tops"],
            "Crop Tops": ["Clothing > Clothing Tops > Crop Tops"],
            "Tube Tops": ["Clothing > Clothing Tops > Tube Tops"],
            "Cardigans": ["Clothing > Clothing Tops > Cardigans"],
            "Sweaters": ["Clothing > Clothing Tops > Sweaters"],
            "Pants": ["Clothing > Bottoms > Pants"],
            "Dresses": ["Clothing > Dresses"],
            "Sets": ["Clothing > Sets", "Clothing > Two-Piece Sets"],
            "Overalls": ["Clothing > One-Piece > Overalls", "Clothing > Jumpsuits & Rompers"]
        }
        
        # First try mapped categories
        if name_lower in CATEGORY_MAP:
            base_paths = CATEGORY_MAP[name_lower]
            logger.debug(f"Found base paths for {name}: {base_paths}")
            for base_path in base_paths:
                full_path = f"Apparel & Accessories > {base_path}"
                if full_path in self.path_to_gid:
                    matches.append(full_path)
                    logger.debug(f"Found valid path: {full_path}")
        
        # If no matches, try exact category name matches
        if not matches:
            logger.debug("Trying exact category name matches")
            for cat_id, cat_data in self.categories.items():
                cat_name = cat_data.get('name', '').lower()
                if cat_name == name_lower:
                    path = cat_data.get('path')
                    if path:
                        matches.append(path)
                        logger.debug(f"Found exact match: {path}")
        
        # If still no matches, try partial matches
        if not matches:
            logger.debug("Trying partial category name matches")
            for cat_id, cat_data in self.categories.items():
                cat_name = cat_data.get('name', '').lower()
                if name_lower in cat_name or cat_name in name_lower:
                    path = cat_data.get('path')
                    if path and "Apparel & Accessories" in path:
                        matches.append(path)
                        logger.debug(f"Found partial match: {path}")
        
        logger.debug(f"Found {len(matches)} total matches")
        return matches

    def load_taxonomy_data(self) -> None:
        """Load taxonomy data from JSON files"""
        mappings_file = self.taxonomy_dir / 'all_mappings.json'
        logger.debug(f"Looking for mappings file at: {mappings_file}")
        
        if not mappings_file.exists():
            raise FileNotFoundError(f"Taxonomy mappings file not found at {mappings_file}")
        
        logger.debug(f"Found mappings file, size: {mappings_file.stat().st_size} bytes")
        
        try:
            with mappings_file.open() as f:
                data = json.load(f)
                logger.debug("Successfully loaded JSON data")
                logger.debug(f"Keys in data: {list(data.keys())}")
                
                mappings = data.get('mappings', {})
                
                # Load categories
                self.categories = {}
                self.path_to_gid = {}
                self.gid_to_path = {}
                self.category_attributes = {}
                
                for gid, cat_data in mappings.get('categories', {}).items():
                    self.categories[gid] = cat_data
                    path = cat_data.get('path')
                    if path:
                        self.path_to_gid[path] = gid
                        self.gid_to_path[gid] = path
                    self.category_attributes[gid] = set(cat_data.get('allowed_attributes', []))
                    
                # Load attributes
                self.attributes = mappings.get('attributes', {})
                
                # Load values with attribute relationships
                self.values = {}
                for value_id, value_data in mappings.get('values', {}).items():
                    self.values[value_id] = {
                        'name': value_data.get('name'),
                        'handle': value_data.get('handle'),
                        'attribute_id': value_data.get('attribute_id'),
                        'description': value_data.get('description'),
                        'meta': value_data.get('meta', {})
                    }
                    
                logger.debug(f"Loaded {len(self.categories)} categories")
                logger.debug(f"Loaded {len(self.attributes)} attributes")
                logger.debug(f"Loaded {len(self.values)} values")
                
                # Log raw value data structure
                sample_value = next(iter(mappings.get('values', {}).items()))
                logger.debug(f"Sample raw value data: {json.dumps(sample_value, indent=2)}")
                
        except Exception as e:
            logger.error(f"Failed to load taxonomy data: {e}")
            raise

    def get_attribute_id_by_handle(self, handle: str) -> Optional[str]:
        """Get attribute ID from its handle"""
        # Use cached mapping if available
        if not hasattr(self, 'handle_to_attribute_id'):
            self.handle_to_attribute_id = {
                attr_data["handle"]: attr_id 
                for attr_id, attr_data in self.attributes.items()
                if "handle" in attr_data
            }
        
        attr_id = self.handle_to_attribute_id.get(handle)
        if attr_id:
            logger.debug(f"Found attribute ID for handle '{handle}': {attr_id}")
        else:
            logger.debug(f"No attribute ID found for handle '{handle}'")
        return attr_id

    def get_value_id_by_name(self, attr_id: str, value_name: str) -> Optional[str]:
        """Get taxonomy value ID by name"""
        try:
            # Get attribute handle
            attr_info = self.attributes.get(attr_id)
            if not attr_info:
                logger.warning(f"No attribute info found for {attr_id}")
                return None
            
            attr_handle = attr_info.get('handle')
            if not attr_handle:
                logger.warning(f"No handle found for attribute {attr_id}")
                return None
            
            # For sizes, map short names to long format
            if attr_handle == 'size':
                # Map short names to taxonomy handles
                size_mappings = {
                    's': 'small-s',
                    'm': 'medium-m',
                    'l': 'large-l',
                    'xs': 'extra-small-xs',
                    'xl': 'extra-large-xl',
                    '2xl': 'double-extra-large-xxl',
                    '3xl': 'triple-extra-large-xxxl',
                    '4xl': 'four-extra-large-4xl',
                    '5xl': 'five-extra-large-5xl'
                }
                
                # Convert short name to long format
                long_name = size_mappings.get(value_name.lower(), value_name)
                expected_handle = f"{attr_handle}__{long_name}"
                logger.debug(f"Looking for size with handle: {expected_handle}")
                
                # Search through values
                for value_id, value_info in self.values.items():
                    if value_info.get('handle') == expected_handle:
                        logger.debug(f"Found matching value: {value_id}")
                        return value_id
                    
                logger.warning(f"No size value found with handle {expected_handle}")
                return None
            else:
                # For other attributes, use normal lookup
                expected_handle = f"{attr_handle}__{value_name.lower().replace(' ', '-')}"
                for value_id, value_info in self.values.items():
                    if value_info.get('handle') == expected_handle:
                        logger.debug(f"Found matching value: {value_id}")
                        return value_id
                
                logger.warning(f"No value found with handle {expected_handle}")
                return None
            
        except Exception as e:
            logger.error(f"Error getting value ID: {str(e)}")
            return None

    def get_attribute_values(self, attribute_id: str) -> List[Dict]:
        """Get all valid values for an attribute with their names and IDs"""
        values = []
        for value_id, value_info in self.values.items():
            if value_info.get('attribute_id') == attribute_id:
                values.append({
                    'id': value_id,
                    'name': value_info['name'],
                    'handle': value_info.get('handle', '')
                })
        return values

    def get_valid_values(self, attribute_id: str) -> List[Dict[str, str]]:
        """Get list of valid values for an attribute"""
        attribute = self.attributes.get(attribute_id, {})
        return attribute.get('values', [])
        
    def get_handle_for_taxonomy_id(self, attribute_type: str, taxonomy_id: str) -> Optional[str]:
        """Get the handle for a taxonomy ID"""
        try:
            # Get value info from values data
            full_gid = f"gid://shopify/TaxonomyValue/{taxonomy_id}" if not taxonomy_id.startswith('gid://') else taxonomy_id
            value_info = self.values.get(full_gid)
            if not value_info:
                logger.warning(f"No value found for {attribute_type} taxonomy ID {taxonomy_id}")
                logger.debug(f"Looking for: {full_gid}")
                logger.debug(f"Available values sample: {list(self.values.keys())[:5]}")
                return None
            
            # Get the handle which contains both attribute and value
            handle = value_info.get('handle')
            if not handle or '__' not in handle:
                logger.warning(f"Invalid handle format in value info: {value_info}")
                return None
            
            logger.debug(f"Found value info: {value_info} for {attribute_type} taxonomy ID {taxonomy_id}")
            
            # Return the full handle (e.g. "waist-rise__low")
            return handle
            
        except Exception as e:
            logger.error(f"Error getting handle for taxonomy ID: {str(e)}")
            return None

    def get_metaobject_gid(self, taxonomy_value_id: str) -> Optional[str]:
        """Get metaobject GID for a taxonomy value"""
        try:
            # Handle both full GID and ID-only formats
            if not taxonomy_value_id.startswith('gid://'):
                full_gid = f"gid://shopify/TaxonomyValue/{taxonomy_value_id}"
            else:
                full_gid = taxonomy_value_id

            logger.debug(f"Looking up taxonomy value with GID: {full_gid}")
            logger.debug(f"Total values loaded: {len(self.values)}")
            logger.debug(f"Values data keys sample: {list(self.values.keys())[:5]}")

            # Get value info from taxonomy data
            value_info = self.values.get(full_gid)
            if not value_info:
                logger.warning(f"No value found for taxonomy ID {taxonomy_value_id}")
                return None

            logger.debug(f"Found value info: {value_info}")

            # Get attribute handle and value name
            handle = value_info.get('handle', '')
            if not handle or '__' not in handle:
                logger.warning(f"Invalid handle format: {handle}")
                return None

            # Split handle into attribute and value parts
            attr_handle, value_handle = handle.split('__')
            logger.debug(f"Split handle into: attr={attr_handle}, value={value_handle}")

            # Look up in GID cache - note the cache structure is different
            attr_values = self.gid_cache.get(attr_handle)
            if not attr_values:
                logger.warning(f"No cache entry found for attribute: {attr_handle}")
                return None

            # Look up value in attribute cache
            metaobject_gid = attr_values.get(value_handle)
            if metaobject_gid:
                logger.debug(f"✅ Found metaobject GID in cache: {metaobject_gid}")
                return metaobject_gid
            else:
                logger.warning(f"No cache entry found for value '{value_handle}' in {attr_handle}")
                return None

        except Exception as e:
            logger.error(f"Error resolving metaobject GID: {str(e)}")
            logger.error(f"Stack trace:", exc_info=True)
            return None

    def get_handle_from_attribute_id(self, attr_id: str) -> Optional[str]:
        """Get attribute handle from ID"""
        attr_info = self.attributes.get(attr_id)
        if attr_info:
            return attr_info.get('handle')
        return None

def main():
    """Example usage"""
    mapper = TaxonomyMapper()
    
    # Example: Look up category GID
    path = "Apparel & Accessories > Shirts & Tops"
    category_id = mapper.get_category_id_from_path(path)
    if category_id:
        print(f"\nCategory path: {path}")
        print(f"Category GID: {category_id}")
        
        # Get allowed attributes
        allowed_attrs = mapper.get_allowed_attribute_ids(category_id)
        print(f"Allowed attributes: {len(allowed_attrs)}")
        
        # Format some example data
        product_data = mapper.format_graphql_input(
            product_id="gid://shopify/Product/123",
            category_id=category_id,
            attributes={
                "gid://shopify/TaxonomyAttribute/sleeve_length": "Short Sleeve",
                "gid://shopify/TaxonomyAttribute/neckline": "Crew Neck"
            }
        )
        print("\nFormatted GraphQL input:")
        print(json.dumps(product_data, indent=2))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
