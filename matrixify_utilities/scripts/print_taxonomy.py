from matrixify_utilities.api.client import ShopifyClient

def main():
    client = ShopifyClient()
    client.print_taxonomy_hierarchy()

if __name__ == "__main__":
    main() 