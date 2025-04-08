from matrixify_utilities.api.client import ShopifyClient
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG)

def main():
    # Load mappings directly first to verify file
    mappings_file = Path(__file__).parent.parent / 'data' / 'all_mappings.json'
    print(f"\nChecking mappings file: {mappings_file}")
    
    try:
        with open(mappings_file, 'r') as f:
            data = json.load(f)
        
        mappings = data.get('mappings', [{}])[0].get('rules', [])
        print("✓ Successfully loaded mappings file")
        print(f"Found {len(mappings)} total rules")
        
        # Print the structure of the first few rules
        print("\nFirst few rules:")
        for i, rule in enumerate(mappings[:3]):
            print(f"\nRule {i+1}:")
            print(f"Input Category: {rule['input']['category']['full_name']}")
            print(f"Input ID: {rule['input']['category']['id']}")
            print(f"Output Category: {rule['output']['category'][0]['full_name']}")
            print(f"Output ID: {rule['output']['category'][0]['id']}")
    except Exception as e:
        print(f"✗ Error loading mappings file: {e}")
        return

    # Test taxonomy helper
    client = ShopifyClient()
    taxonomy_helper = client.taxonomy_helper
    
    # Test looking up some common categories
    test_categories = ["Dresses", "T-Shirts", "Pants", "Skirts"]
    
    print("\nTesting category lookups:")
    for category_name in test_categories:
        result = taxonomy_helper.get_category_by_name(category_name)
        if result:
            print(f"\n{category_name}:")
            print(f"  Full Name: {result['full_name']}")
            print(f"  Numeric ID: {result['numeric_id']}")
            print(f"  Taxonomy ID: {result['taxonomy_id']}")
        else:
            print(f"\n✗ Could not find category: {category_name}")
    
    # Show some example full category paths
    print("\nExample category paths:")
    categories = taxonomy_helper.list_categories()
    for i, category in enumerate(categories[:5], 1):
        print(f"\n{i}. {category['full_name']}")
        print(f"   Numeric ID: {category['numeric_id']}")
        print(f"   Taxonomy ID: {category['taxonomy_id']}")

if __name__ == "__main__":
    main() 