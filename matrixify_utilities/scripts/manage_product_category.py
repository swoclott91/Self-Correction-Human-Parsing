import json
from matrixify_utilities.api.client import ShopifyClient

def get_available_categories(client):
    """Get list of available categories from products"""
    query = """
    query {
        shop {
            productTaxonomyNode {
                id
                name
                fullName
            }
        }
    }
    """
    
    result = client.graphql_query(query)
    categories = {}
    
    # Add the root taxonomy node
    if result.get('data', {}).get('shop', {}).get('productTaxonomyNode'):
        node = result['data']['shop']['productTaxonomyNode']
        categories[node['id']] = {
            'name': node['name'],
            'fullName': node['fullName']
        }
    
    return categories

def print_product_info(client, product_id: str):
    """Print current product category information"""
    query = """
    query getProduct($id: ID!) {
        product(id: $id) {
            id
            title
            productType
            productCategory {
                productTaxonomyNode {
                    id
                    name
                    fullName
                }
            }
        }
    }
    """
    
    product_gid = f"gid://shopify/Product/{product_id}" if not product_id.startswith('gid://') else product_id
    result = client.graphql_query(query, {"id": product_gid})
    
    if result.get('data', {}).get('product'):
        product = result['data']['product']
        print("\nCurrent Product Information:")
        print(f"Title: {product['title']}")
        print(f"Product Type: {product['productType']}")
        if product.get('productCategory', {}).get('productTaxonomyNode'):
            category = product['productCategory']['productTaxonomyNode']
            print(f"Category: {category['fullName']} (ID: {category['id'].split('/')[-1]})")
        else:
            print("No category assigned")

def main():
    client = ShopifyClient()
    product_id = "14697141109108"  # Your dress product
    
    # Show current product info
    print_product_info(client, product_id)
    
    # Get and show available categories
    categories = get_available_categories(client)
    
    print("\nAvailable Categories:")
    for category_id, details in categories.items():
        print(f"\nCategory: {details['fullName']}")
        print(f"ID: {category_id.split('/')[-1]}")
    
    # Allow updating to a specific category
    print("\nWould you like to update the product category? (y/n)")
    if input().lower() == 'y':
        print("\nEnter the category ID:")
        category_id = input().strip()
        success = client.update_product_taxonomy(product_id, category_id)
        if success:
            print("\nUpdate successful!")
            print_product_info(client, product_id)
        else:
            print("\nUpdate failed!")

if __name__ == "__main__":
    main() 