import json
from matrixify_utilities.api.client import ShopifyClient

def main():
    client = ShopifyClient()
    structure = client.get_taxonomy_structure()
    
    print("\nProduct Types:")
    for path, details in structure.items():
        if details.get('type') == 'product_type':
            print(f"- {details['name']}")
    
    print("\nTaxonomy Categories:")
    for path, details in structure.items():
        if details.get('type') == 'taxonomy_node':
            print(f"\nFull Path: {path}")
            print(f"ID: {details['id']}")
            print(f"Name: {details['name']}")
            if details.get('product_type'):
                print(f"Product Type: {details['product_type']}")

if __name__ == "__main__":
    main() 