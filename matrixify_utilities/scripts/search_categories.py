from matrixify_utilities.api.client import ShopifyClient
import sys

def search_by_id(taxonomy_helper, numeric_id: str):
    """Find all categories with a specific numeric ID"""
    categories = taxonomy_helper.list_categories()
    matching = [
        cat for cat in categories 
        if cat['numeric_id'] == numeric_id
    ]
    
    if matching:
        print(f"\nFound {len(matching)} categories with ID {numeric_id}:")
        for i, category in enumerate(matching, 1):
            print(f"\n{i}. {category['full_name']}")
            print(f"   Taxonomy ID: {category['taxonomy_id']}")
    else:
        print(f"\nNo categories found with ID {numeric_id}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python search_categories.py <search term or ID>")
        print("Examples:")
        print("  python search_categories.py Dresses")
        print("  python search_categories.py --id 2271")
        return

    client = ShopifyClient()
    taxonomy_helper = client.taxonomy_helper
    
    # Check if we're searching by ID
    if sys.argv[1] == '--id':
        if len(sys.argv) < 3:
            print("Please provide an ID to search for")
            return
        search_by_id(taxonomy_helper, sys.argv[2])
        return
    
    search_term = sys.argv[1]
    print(f"\nSearching for categories containing '{search_term}':")
    
    # Get all categories
    categories = taxonomy_helper.list_categories()
    
    # Filter and sort by path length (shorter paths first)
    matching = [
        cat for cat in categories 
        if search_term.lower() in cat['full_name'].lower()
    ]
    matching.sort(key=lambda x: len(x['full_name'].split(' > ')))
    
    if matching:
        print(f"\nFound {len(matching)} matching categories:")
        for i, category in enumerate(matching, 1):
            print(f"\n{i}. {category['full_name']}")
            print(f"   Numeric ID: {category['numeric_id']}")
            print(f"   Taxonomy ID: {category['taxonomy_id']}")
    else:
        print(f"\nNo categories found containing '{search_term}'")

if __name__ == "__main__":
    main() 