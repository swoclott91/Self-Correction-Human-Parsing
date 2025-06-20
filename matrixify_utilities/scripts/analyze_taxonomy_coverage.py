import logging
from pathlib import Path
import json
from pprint import pprint
from matrixify_utilities.scripts.taxonomy_mapper import TaxonomyMapper
from matrixify_utilities.scripts.clothing_categorizer import ClothingCategorizer

logger = logging.getLogger(__name__)

def load_json_file(filepath: Path) -> dict:
    """Load and parse JSON file"""
    with open(filepath) as f:
        return json.load(f)

def analyze_category_coverage():
    """Analyze which categories are covered and which are missing"""
    mapper = TaxonomyMapper()
    
    # Get all available categories from taxonomy
    all_categories = set()
    for category in mapper.categories.values():
        if isinstance(category, dict) and category.get('path', '').startswith('Apparel & Accessories'):
            path = category['path'].replace('Apparel & Accessories > ', '')
            all_categories.add(path)
    
    # Get currently covered categories
    covered_categories = set(ClothingCategorizer.CATEGORY_KEYWORDS.keys())
    
    # Find missing categories
    missing_categories = all_categories - covered_categories
    
    # Print analysis
    print("\nCategory Coverage Analysis:")
    print("==========================")
    print("\nCurrently Covered Categories:")
    for category in sorted(covered_categories):
        print(f"- {category}")
        print(f"  Keywords: {', '.join(ClothingCategorizer.CATEGORY_KEYWORDS[category])}")
    
    print("\nMissing Categories:")
    for category in sorted(missing_categories):
        print(f"- {category}")
        # Suggest some keywords based on category name
        suggested_keywords = []
        words = category.lower().replace('&', 'and').split()
        suggested_keywords.append(category.lower())
        if len(words) > 1:
            suggested_keywords.extend([w for w in words if len(w) > 3])
        print(f"  Suggested keywords: {', '.join(suggested_keywords)}")

def analyze_attribute_coverage():
    """Analyze coverage of taxonomy attributes in ATTRIBUTE_PATTERNS"""
    
    # Initialize TaxonomyMapper
    taxonomy_dir = Path(__file__).parent.parent / 'taxonomy_data'
    mapper = TaxonomyMapper(taxonomy_dir)
    
    # Load categories
    categories_data = load_json_file(taxonomy_dir / 'categories.json')
    categories = categories_data.get('data', {})
    
    # Filter for Apparel & Accessories categories
    apparel_categories = {}
    for cat_id, cat_data in categories.items():
        if isinstance(cat_data, dict) and cat_data.get('path', '').startswith('Apparel & Accessories'):
            apparel_categories[cat_id] = cat_data
            # Also add all child categories
            for child_id in cat_data.get('children', []):
                if child_id in categories:
                    apparel_categories[child_id] = categories[child_id]
            
    logger.info(f"Found {len(apparel_categories)} apparel categories")
    
    # Collect all allowed attributes
    allowed_attributes = set()
    for cat_data in apparel_categories.values():
        allowed_attrs = cat_data.get('allowed_attributes', [])
        if isinstance(allowed_attrs, list):
            allowed_attributes.update(allowed_attrs)
            
    logger.info(f"Found {len(allowed_attributes)} unique allowed attributes")
    
    # Build complete attribute → value mapping using TaxonomyMapper
    taxonomy_mapping = {}
    for attr_id in allowed_attributes:
        attr_info = mapper.get_attribute_info(attr_id)
        if attr_info:
            attr_name = attr_info.get('handle')
            logger.debug(f"\nProcessing attribute {attr_id}: {attr_name}")
            
            # Get values directly from the values array
            values = attr_info.get('values', [])
            logger.debug(f"Found {len(values)} values")
            
            allowed_values = []
            for value in values:
                if isinstance(value, dict):
                    value_name = value.get('name')
                    if value_name:
                        logger.debug(f"  Adding value: {value_name}")
                        allowed_values.append(value_name)
                    else:
                        logger.debug(f"  No name found in value: {value}")
                else:
                    logger.debug(f"  Invalid value format: {value}")
                    
            if allowed_values:  # Only add if there are values
                taxonomy_mapping[attr_name] = allowed_values
                logger.debug(f"Added {len(allowed_values)} values for {attr_name}")
            else:
                logger.debug(f"No values found for {attr_name}")
                
    logger.debug(f"Built taxonomy mapping with {len(taxonomy_mapping)} attributes")
    logger.debug("Taxonomy mapping:")
    pprint(taxonomy_mapping)
    
    # Import ClothingCategorizer
    current_patterns = ClothingCategorizer.ATTRIBUTE_PATTERNS
    logger.debug(f"Loaded {len(current_patterns)} patterns from ATTRIBUTE_PATTERNS")
    
    # Find missing attributes
    missing_attrs = set(taxonomy_mapping.keys()) - set(current_patterns.keys())
    print("\nAttributes not covered in ATTRIBUTE_PATTERNS:")
    for attr in sorted(missing_attrs):
        print(f"- {attr}")
        print(f"  Allowed values: {sorted(taxonomy_mapping[attr])}")
        
    # Find missing values for covered attributes
    print("\nMissing values for covered attributes:")
    for attr, patterns in sorted(current_patterns.items()):
        if attr in taxonomy_mapping:
            missing_values = set(taxonomy_mapping[attr]) - set(patterns.keys())
            if missing_values:
                print(f"\n{attr}:")
                for value in sorted(missing_values):
                    print(f"  - {value}")
                    # Generate suggested regex
                    suggested_regex = f"r\"{value.lower()}|{value.lower().replace(' ', '[- ]')}\""
                    print(f"    Suggested regex: {suggested_regex}")

def main():
    """Run the analysis"""
    import argparse
    parser = argparse.ArgumentParser(description='Analyze taxonomy coverage')
    parser.add_argument('--type', choices=['categories', 'attributes', 'all'], 
                       default='all', help='Type of analysis to run')
    args = parser.parse_args()
    
    if args.type in ['categories', 'all']:
        analyze_category_coverage()
    if args.type in ['attributes', 'all']:
        analyze_attribute_coverage()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()