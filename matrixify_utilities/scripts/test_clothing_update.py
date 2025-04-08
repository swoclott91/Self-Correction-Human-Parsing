import logging
from pathlib import Path
from typing import Dict, List
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
import os
from dotenv import load_dotenv

# Update the import path to be relative to the current file
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from matrixify_utilities.api.client import ShopifyClient
from .enrich_product_data import ProductEnricher

logger = logging.getLogger(__name__)
console = Console()

class EnrichmentTester:
    """Tests product enrichment pipeline with real Shopify products"""
    
    PRODUCTS_QUERY = """
    query {
      products(first: 10, sortKey: CREATED_AT, reverse: true) {
        edges {
          node {
            id
            title
            descriptionHtml
            createdAt
            status
          }
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
        
    def fetch_recent_products(self) -> List[Dict]:
        """Fetch recent products from Shopify"""
        try:
            response = self.client.execute_query(self.PRODUCTS_QUERY)
            
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
                        'status': node.get('status', 'UNKNOWN')
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

    def test_enrichment(self, products: List[Dict]) -> None:
        """Test enrichment pipeline on products"""
        if not products:
            console.print("[red]No products to process[/red]")
            return
        
        # Lower confidence threshold for testing
        self.enricher.confidence_threshold = 0.1
        
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
            skip_low_confidence=False  # Don't skip low confidence matches
        )
        
        # Track success/failure counts
        total = len(products)
        success_count = len(successful)
        fail_count = len(failed)
        
        # Add successful results to table
        for payload in successful:
            product_id = payload['id'].split('/')[-1]  # Strip gid prefix
            
            # Find original product data
            product = next(p for p in products if p['product_id'] == payload['id'])
            
            # Format attributes nicely
            attributes = []
            for field in payload['metafields']:
                attributes.append(f"{field['key']}: {field['value']}")
            attributes_str = "\n".join(attributes)
            
            table.add_row(
                product_id,
                product['title'][:40] + "..." if len(product['title']) > 40 else product['title'],
                payload['category'].split('/')[-1],  # Strip gid prefix
                "✓",
                attributes_str if attributes else "None",
                "SUCCESS"
            )
            
        # Add failed results to table with more detail
        for result in failed:
            product_id = result['product_id'].split('/')[-1]
            
            # Find original product data
            product = next(p for p in products if p['product_id'] == result['product_id'])
            
            # Show top category matches
            if 'matches' in result:
                matches = "\n".join([f"{m['category']}: {m['confidence']:.2f}" 
                                   for m in result['matches'][:3]])
            else:
                matches = "No matches found"
            
            table.add_row(
                product_id,
                product['title'][:40] + "..." if len(product['title']) > 40 else product['title'],
                "N/A",
                f"{result['confidence']:.2f}" if 'confidence' in result else "N/A",
                matches,
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
        level=logging.DEBUG,  # Change to DEBUG level
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    shop_url = os.getenv('SHOPIFY_SHOP_URL')
    access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
    debug_mode = True  # Force debug mode on
    
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
    
    # Fetch products
    console.print("[yellow]Fetching recent products...[/yellow]")
    products = tester.fetch_recent_products()
    
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
