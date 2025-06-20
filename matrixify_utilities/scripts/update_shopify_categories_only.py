# This script only updates categories and skips attribute metafield updates.

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
import os
from dotenv import load_dotenv

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Now import our local modules
from matrixify_utilities.api.client import ShopifyClient
from matrixify_utilities.scripts.enrich_product_data import ProductEnricher
from matrixify_utilities.scripts.metaobject_helper import MetaobjectResolver

logger = logging.getLogger(__name__)
console = Console()

class EnrichmentTester:
    """Tests product enrichment pipeline with real Shopify products"""
    
    PRODUCTS_QUERY = """
    query GetProducts($limit: Int!, $query: String) {
      products(
        first: $limit, 
        sortKey: CREATED_AT, 
        reverse: true,
        query: $query
      ) {
        edges {
          node {
            id
            title
            descriptionHtml
            createdAt
            status
            options {
              name
              values
            }
            variants(first: 20) {
              edges {
                node {
                  id
                  title
                  selectedOptions {
                    name
                    value
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    # Update mutation to use correct input type
    UPDATE_PRODUCT_MUTATION = """
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product {
          id
          title
          category {
            name
            path
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    def __init__(self, 
                 shop_url: str,
                 access_token: str,
                 taxonomy_dir: Path = None,
                 debug_mode: bool = False):
        """Initialize with shop credentials"""
        self.client = ShopifyClient(
            shop_url=shop_url, 
            access_token=access_token,
            validate_schema=False  # Skip schema validation
        )
        self.enricher = ProductEnricher(
            taxonomy_dir=taxonomy_dir,
            confidence_threshold=0.5
        )
        self.debug_mode = debug_mode
        
        # Initialize metaobject resolver
        self.metaobject_resolver = MetaobjectResolver(
            shop_url=shop_url,
            access_token=access_token
        )
        
        # Pre-warm cache with known types
        self.metaobject_resolver.warm_cache([
            "shopify--age-group",
            "shopify--fabric", 
            "shopify--target-gender",
            "shopify--skirt-dress-length-type",
            "shopify--dress-occasion"
        ])
        
    def fetch_recent_products(self, limit: int = 10, status: str = None) -> List[Dict]:
        """
        Fetch recent products from Shopify
        
        Args:
            limit: Maximum number of products to fetch
            status: Filter by status (e.g., 'draft', 'active')
        """
        try:
            # Build query variables
            variables = {
                "limit": limit,
                "query": f"status:{status.upper()}" if status else None
            }
            
            logger.debug(f"Fetching products with variables: {variables}")
            
            response = self.client.execute_query(
                self.PRODUCTS_QUERY,
                variables=variables
            )
            
            logger.debug("Raw API response:")
            logger.debug(json.dumps(response, indent=2))
            
            # Basic response validation
            if not response or not isinstance(response, dict):
                logger.error(f"Invalid response: {response}")
                return []
            
            # Extract products data - handle both possible response structures
            edges = (response.get('data', {}).get('products', {}) or response.get('products', {})).get('edges', [])
            
            logger.debug(f"Found {len(edges)} edges in response")
            
            products = []
            for i, edge in enumerate(edges):
                try:
                    node = edge.get('node', {})
                    logger.debug(f"Processing node {i}:")
                    logger.debug(json.dumps(node, indent=2))
                    
                    if not node:
                        logger.warning(f"Edge {i} has no node data")
                        continue
                    
                    # Validate required fields
                    if not node.get('id'):
                        logger.warning(f"Node {i} missing required ID field")
                        continue
                    
                    product = {
                        'product_id': node['id'],
                        'title': node.get('title', 'Untitled'),
                        'description': node.get('descriptionHtml', ''),
                        'created_at': node.get('createdAt'),
                        'status': node.get('status', 'UNKNOWN'),
                        'options': node.get('options', []),
                        'variants': [
                            {
                                'id': variant['node']['id'],
                                'title': variant['node']['title'],
                                'selected_options': variant['node'].get('selectedOptions', [])
                            }
                            for variant in node.get('variants', {}).get('edges', [])
                        ] if 'variants' in node else []
                    }
                    
                    logger.debug(f"Created product object:")
                    logger.debug(json.dumps(product, indent=2))
                    
                    products.append(product)
                    logger.info(f"Successfully processed product: {product['title']}")
                    
                except Exception as e:
                    logger.error(f"Error processing edge {i}: {str(e)}", exc_info=True)
                    continue
            
            if products:
                logger.info(f"Successfully fetched {len(products)} products")
                return products
            else:
                logger.warning("No products processed from response")
                logger.debug("Response structure:")
                logger.debug(f"Response keys: {list(response.keys())}")
                if 'products' in response:
                    logger.debug(f"Products keys: {list(response['products'].keys())}")
                    if 'edges' in response['products']:
                        logger.debug(f"Number of edges: {len(response['products']['edges'])}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to fetch products: {str(e)}", exc_info=True)
            return []

    def _resolve_metafield_value(self, field: dict) -> Optional[str]:
        """
        Resolve metafield value, handling taxonomy values through metaobjects
        """
        key = field.get('key')
        value = field.get('value')
        
        if not key or not value:
            return None
            
        try:
            # For taxonomy values, get the display name and create metaobject
            if value.startswith('gid://shopify/TaxonomyValue/'):
                # Get the attribute info from taxonomy
                attribute_info = self.enricher.mapper.get_attribute_info(key)
                if not attribute_info:
                    logger.warning(f"[ATTR] Could not find attribute info for: {key}")
                    return None
                
                # Get the value name from taxonomy values
                value_info = self.enricher.mapper.get_value_info(value)
                if not value_info or 'name' not in value_info:
                    logger.warning(f"[ATTR] Could not find value info for: {value}")
                    return None
                
                value_name = value_info['name']
                
                # Create metaobject type from attribute key
                metaobject_type = f"shopify--{key}"
                
                # Get or create metaobject for this taxonomy value
                metaobject_gid = self.metaobject_resolver.get_or_create_value_gid(
                    metaobject_type=metaobject_type,
                    handle=value_name.lower().replace(' ', '-'),
                    label=value_name
                )
                
                if metaobject_gid:
                    logger.info(f"[ATTR] Mapped taxonomy value {key}={value_name} to metaobject: {metaobject_gid}")
                    return metaobject_gid
                else:
                    logger.warning(f"[ATTR] Failed to create metaobject for {key}={value_name}")
                    return None
                    
            # For custom attributes, use direct metaobject references
            else:
                metaobject_type = f"shopify--{key}"
                value_gid = self.metaobject_resolver.get_or_create_value_gid(
                    metaobject_type=metaobject_type,
                    handle=value.lower().replace(' ', '-'),
                    label=value.replace('-', ' ').title()
                )
                
                if value_gid:
                    logger.info(f"[ATTR] Created custom metaobject for {key} -> {value_gid}")
                    return value_gid
                else:
                    logger.warning(f"[ATTR] Could not create metaobject for {key}={value}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error resolving metafield value: {str(e)}")
            return None

    def _update_product(self, product_id: str, category_id: str, metafields: List[Dict]) -> bool:
        """
        Update product with category and metafields in Shopify
        """
        try:
            # Build update payload
            variables = {
                "input": {  # Use input instead of product
                    "id": product_id,
                    "category": category_id,
                }
            }
            
            # Process metafields through metaobject resolution
            # Add metafields if we have any
            logger.debug(f"Updating product {product_id} with variables: {json.dumps(variables, indent=2)}")
            
            response = self.client.execute_query(
                self.UPDATE_PRODUCT_MUTATION,
                variables=variables
            )
            
            if 'errors' in response:
                logger.error(f"GraphQL query failed: {response['errors'][0]}")
                return False
                
            user_errors = response.get('data', {}).get('productUpdate', {}).get('userErrors', [])
            if user_errors:
                for error in user_errors:
                    logger.error(f"Error updating product: {error['message']}")
                return False
                
            logger.info(f"Successfully updated product {product_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update product {product_id}: {str(e)}")
            return False

    def test_enrichment(self, products: List[Dict]) -> None:
        """Test enrichment pipeline on products"""
        if not products:
            console.print("[red]No products to process[/red]")
            return
            
        # Create results table
        table = Table(title="Enrichment Test Results")
        table.add_column("Product ID", style="cyan")
        table.add_column("Title", style="blue")
        table.add_column("Category", style="green")
        table.add_column("Confidence", style="yellow")
        table.add_column("Attributes", style="magenta")
        table.add_column("Status", style="red")
        
        # Process products
        successful, failed = self.enricher.batch_enrich_products(
            products,
            skip_low_confidence=False
        )
        
        # Track success/failure counts
        total = len(products)
        success_count = len(successful)
        fail_count = len(failed)
        
        # Add successful results to table
        for payload in successful:
            # Find original product to get title
            product = next(p for p in products if p['product_id'] == payload['id'])
            
            product_id = payload['id']
            category_id = payload['category']
            
            for field in payload.get('metafields', []):
                metaobject_gid = self._resolve_metafield_value(field)
                if metaobject_gid:
            # Log taxonomy attributes for future API support
                logger.info(f"Taxonomy attributes for future API support: {json.dumps(payload.get('metafields', []), indent=2)}")
            
            # Build mutation payload
            variables = {
                "input": {
                    "id": product_id,
                    "category": category_id
                }
            }
            # Run mutation
            response = self.client.execute_query(
                self.UPDATE_PRODUCT_MUTATION,
                variables=variables
            )
            
            if 'errors' in response or response.get('data', {}).get('productUpdate', {}).get('userErrors'):
                console.print(f"[red]Failed to update product {product_id}[/red]")
                logger.error(f"GraphQL errors: {response.get('errors') or response['data']['productUpdate']['userErrors']}")
            else:
                logger.info(f"Updated product {product_id}")
                console.print(f"[green]Updated product {product_id}[/green]")
            
            # Format display attributes
            display_attrs = []
            if display_attrs:
                logger.info("\n" + "\n".join(display_attrs))
            
            # Extract category info from payload
            category_info = payload.get('category', {})
            if isinstance(category_info, str):
                path = self.enricher.mapper.get_path_from_category_id(category_info)
                # Use product title from original product data
                _, confidence = self.enricher.categorizer.categorize(product['title'])
                category_info = {
                    'gid': category_info,
                    'path': path,
                    'confidence': confidence
                }
            
            # Add row to table with results
            table.add_row(
                product_id,
                product['title'][:40] + "..." if len(product['title']) > 40 else product['title'],
                category_info.get('path', '').split(' > ')[-1] if category_info else "Unknown",
                f"{float(category_info.get('confidence', 0.0)):.2f}",
                "\n".join(display_attrs) if display_attrs else "None",
                "SUCCESS" if not 'errors' in response else "FAILED"
            )
        
        # Add failed results to table with more detail
        for result in failed:
            product_id = result['product_id'].split('/')[-1]
            product = next(p for p in products if p['product_id'] == result['product_id'])
            
            # Show top category matches for failed items
            matches = []
            if 'matches' in result:
                for match in result['matches'][:3]:  # Show top 3 matches
                    matches.append(f"{match['category']}: {match.get('confidence', 0.0):.2f}")
            matches_str = "\n".join(matches) if matches else "No matches found"
            
            table.add_row(
                product_id,
                product['title'][:40] + "..." if len(product['title']) > 40 else product['title'],
                "N/A",
                f"{result.get('confidence', 0.0):.2f}",
                "None",
                matches_str,
                "FAILED"
            )
        
        # Print summary
        console.print("\n")
        console.print(Panel(
            f"Processed {total} products\n"
            f"✅ {success_count} successful\n"
            f"❌ {fail_count} failed",
            title="Summary",
            expand=False
        ))
        
        # Print detailed results
        console.print("\n")
        console.print(table)
        
        # Print example GraphQL payload
        if successful:
            console.print("\nExample GraphQL Payload:")
            console.print(json.dumps(successful[0], indent=2))

def main():
    """Run enrichment tests"""
    # Load environment variables
    load_dotenv()
    
    # Set up logging with DEBUG level
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Add argument parsing
    import argparse
    parser = argparse.ArgumentParser(description='Test product enrichment')
    parser.add_argument('--status', type=str, help='Filter by product status (e.g., draft, active)')
    parser.add_argument('--limit', type=int, default=10, help='Maximum number of products to fetch')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    shop_url = os.getenv('SHOPIFY_SHOP_URL')
    access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
    debug_mode = args.debug
    
    if not shop_url or not access_token:
        console.print("[red]Error: Missing Shopify credentials in .env file[/red]")
        return
    
    # Initialize tester
    console.print("[yellow]Initializing tester...[/yellow]")
    tester = EnrichmentTester(
        shop_url=shop_url,
        access_token=access_token,
        debug_mode=debug_mode
    )
    
    # Fetch products with filters
    console.print("[yellow]Fetching recent products...[/yellow]")
    products = tester.fetch_recent_products(
        limit=args.limit,
        status=args.status
    )
    
    if not products:
        console.print("[red]Error: No products found[/red]")
        return
        
    # Show product details
    console.print(f"\n[green]Found {len(products)} products:[/green]")
    for i, product in enumerate(products, 1):
        console.print(f"\n[cyan]Product {i}:[/cyan]")
        console.print(f"  Title: {product['title']}")
        console.print(f"  ID: {product['product_id']}")
        console.print(f"  Status: {product['status']}")
    
    # Run enrichment
    console.print("\n[yellow]Running enrichment...[/yellow]")
    tester.test_enrichment(products)

if __name__ == "__main__":
    main()