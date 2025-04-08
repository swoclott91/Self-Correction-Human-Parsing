import json
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class TaxonomyMapper:
    """Maps between Shopify category paths and GIDs, provides attribute validation"""
    
    def __init__(self, taxonomy_dir: Optional[Path] = None):
        """Initialize with taxonomy data directory"""
        self.taxonomy_dir = taxonomy_dir or Path(__file__).parent.parent / 'taxonomy_data'
        
        # Load taxonomy data
        self.categories = self._load_json('categories.json')
        self.attributes = self._load_json('attributes.json')
        self.values = self._load_json('values.json')
        
        # Build path -> GID mapping
        self.path_to_gid: Dict[str, str] = {}
        self.gid_to_path: Dict[str, str] = {}
        self._build_path_mappings()
        
        # Cache allowed attributes per category
        self.category_attributes: Dict[str, Set[str]] = {}
        self._build_attribute_mappings()

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
        """Get category GID from a path string"""
        # Try exact match first
        gid = self.path_to_gid.get(path)
        if gid:
            return gid
            
        # Try with "Apparel & Accessories >" prefix if not found
        if not path.startswith("Apparel & Accessories > "):
            prefixed_path = f"Apparel & Accessories > {path}"
            return self.path_to_gid.get(prefixed_path)
            
        return None

    def get_path_from_category_id(self, category_id: str) -> Optional[str]:
        """Get category path from a GID"""
        return self.gid_to_path.get(category_id)

    def get_allowed_attributes(self, category_id: str) -> Set[str]:
        """Get set of allowed attribute GIDs for a category"""
        allowed = self.category_attributes.get(category_id, set())
        logger.debug(f"Category {category_id} allows attributes: {allowed}")
        return allowed

    def get_attribute_info(self, attribute_id: str) -> Optional[Dict]:
        """Get attribute details including name, type, and allowed values"""
        info = self.attributes.get(attribute_id)
        if not info:
            logger.warning(f"No info found for attribute {attribute_id}")
        return info

    def get_valid_values_for_attribute(self, attr_id: str) -> Dict[str, Dict]:
        """Get valid values for an attribute from the taxonomy"""
        # Get the attribute info
        attr_info = self.get_attribute_info(attr_id)
        if not attr_info:
            logger.warning(f"No attribute info found for {attr_id}")
            return {}
        
        # Get all values that belong to this attribute
        valid_values = {}
        for value_id, value_info in self.values.items():
            if value_info.get('attribute_id') == attr_id:
                valid_values[value_id] = value_info
                logger.debug(f"Found valid value for {attr_id}: {value_info['name']}")
            
        if not valid_values:
            logger.warning(f"No valid values found for attribute {attr_id} ({attr_info.get('name')})")
        else:
            logger.debug(f"Found {len(valid_values)} valid values for {attr_info.get('name')}")
        
        return valid_values

    def get_value_info(self, value_id: str) -> Optional[Dict]:
        """Get value details including name and metadata"""
        return self.values.get(value_id)

    def is_valid_attribute_for_category(self, category_id: str, attribute_id: str) -> bool:
        """Check if an attribute is valid for a category"""
        allowed = self.get_allowed_attributes(category_id)
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

    def format_graphql_input(self, product_id: str, category_id: str, 
                           attributes: Dict[str, str]) -> Dict:
        """Format product data for GraphQL productUpdate mutation"""
        
        # Validate category exists
        if category_id not in self.categories:
            raise ValueError(f"Invalid category ID: {category_id}")
            
        # Validate attributes are allowed for category
        allowed_attrs = self.get_allowed_attributes(category_id)
        for attr_id in attributes:
            if attr_id not in allowed_attrs:
                raise ValueError(f"Attribute {attr_id} not allowed for category {category_id}")
                
        # Format metafields
        metafields = []
        for attr_id, value in attributes.items():
            attr_info = self.get_attribute_info(attr_id)
            if not attr_info:
                continue
                
            metafields.append({
                "namespace": "standard",
                "key": attr_info['handle'],
                "value": value,
                "type": attr_info['type']
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
            text: Optional product text to check for special categories
        """
        matches = []
        name = name.lower()
        text = text.lower()
        
        # Check for special category indicators in text
        is_maternity = any(word in text for word in ["maternity", "pregnancy", "pregnant", "expecting"])
        is_plus_size = any(word in text for word in ["plus size", "plus-size", "curvy"])
        is_petite = any(word in text for word in ["petite", "short"])
        
        # First pass: collect all matching paths
        for cat in self.categories.values():
            if cat["name"].lower() == name:
                path = cat["path"]
                
                # Skip special categories unless explicitly indicated
                if not is_maternity and "Maternity" in path:
                    continue
                if not is_plus_size and "Plus Size" in path:
                    continue
                if not is_petite and "Petite" in path:
                    continue
                if "Baby & Toddler" not in path:  # Always skip baby unless it's the only option
                    matches.append(path)
        
        if not matches:
            # If no matches found, try again including all paths
            for cat in self.categories.values():
                if cat["name"].lower() == name:
                    matches.append(cat["path"])
        
        # Sort paths by specificity and relevance
        def path_sort_key(path: str):
            segments = path.split(" > ")
            penalty = 0
            
            # Penalize special categories
            if "Baby & Toddler" in path:
                penalty += 100
            if "Maternity" in path and not is_maternity:
                penalty += 90
            if "Plus Size" in path and not is_plus_size:
                penalty += 80
            if "Petite" in path and not is_petite:
                penalty += 80
            if "Costumes" in path:
                penalty += 70
            if "Traditional & Ceremonial" in path:
                penalty += 60
            if "Uniforms" in path:
                penalty += 50
            if "Workwear" in path:
                penalty += 40
            
            # Boost standard clothing paths
            boost = 0
            if "Clothing > Tops" in path:
                boost += 20
            if "Clothing > Dresses" in path:
                boost += 20
            if "Clothing > Bottoms" in path:
                boost += 20
            
            return (-len(segments), penalty - boost)
        
        matches.sort(key=path_sort_key)
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
        for attr_id, attr_info in self.attributes.items():
            if attr_info.get('handle') == handle:
                return attr_id
        return None

    def get_value_id_by_name(self, attribute_id: str, value_name: str, threshold: float = 0.85) -> Optional[str]:
        """Get value ID by attribute ID and value name using flexible matching"""
        valid_values = self.get_valid_values_for_attribute(attribute_id)
        value_name = value_name.lower()
        
        # First try exact match
        for value_id, value_info in valid_values.items():
            if value_info['name'].lower() == value_name:
                logger.debug(f"Exact match found for {value_name}: {value_info['name']}")
                return value_id
            
        # Then try partial match
        for value_id, value_info in valid_values.items():
            if value_name in value_info['name'].lower() or value_info['name'].lower() in value_name:
                logger.debug(f"Partial match found for {value_name}: {value_info['name']}")
                return value_id
            
        # Finally try fuzzy matching
        best_match = None
        best_ratio = 0
        
        for value_id, value_info in valid_values.items():
            ratio = SequenceMatcher(None, value_name, value_info['name'].lower()).ratio()
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = value_id
            
        if best_match:
            logger.debug(f"Fuzzy match found for {value_name}: {valid_values[best_match]['name']} (score: {best_ratio:.2f})")
            return best_match
            
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
        allowed_attrs = mapper.get_allowed_attributes(category_id)
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
