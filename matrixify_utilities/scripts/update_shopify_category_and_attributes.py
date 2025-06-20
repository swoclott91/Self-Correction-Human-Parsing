import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
import os
from dotenv import load_dotenv
import csv
from datetime import datetime
import argparse
import time

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
    query GetProducts($pageSize: Int!, $cursor: String, $query: String) {
        products(first: $pageSize, after: $cursor, query: $query) {
            pageInfo {
                hasNextPage
                endCursor
            }
            edges {
                node {
                    id
                    title
                    descriptionHtml
                    createdAt
                    status
                    productCategory {
                        productTaxonomyNode {
                            id
                            fullName
                        }
                    }
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
    
    # Update mutation to match Shopify's expected format
    UPDATE_PRODUCT_CATEGORY_MUTATION = """
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product {
          id
          title
          productCategory {
            productTaxonomyNode {
              id
              fullName
            }
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    UPDATE_PRODUCT_METAFIELDS_MUTATION = """
    mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields {
          id
          key
          value
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
        
    def fetch_recent_products(self, limit: int = 250, status: str = None, uncategorized: bool = False) -> List[Dict]:
        """Fetch recent products from Shopify using pagination"""
        try:
            # Build query filters
            query_parts = []
            
            # Add status filter
            if status:
                query_parts.append(f"status:{status.upper()}")
                logger.debug(f"Added status filter: status:{status.upper()}")
            
            # Note: product_category:null doesn't work in API, we'll filter after fetching
            query_string = " AND ".join(query_parts) if query_parts else None
            logger.info(f"Using query string: {query_string}")
            
            all_products = []
            cursor = None
            
            while len(all_products) < limit:
                batch_size = min(50, limit - len(all_products))
                
                variables = {
                    "pageSize": batch_size,
                    "cursor": cursor,
                    "query": query_string
                }
                
                logger.debug(f"Fetching batch with variables: {variables}")
                
                response = self.client.execute_query(
                    self.PRODUCTS_QUERY,
                    variables=variables
                )
                
                if 'errors' in response:
                    logger.error(f"GraphQL errors: {response['errors']}")
                    break
                
                products_data = response.get('products', {})
                edges = products_data.get('edges', [])
                
                # Debug edges
                logger.debug("Number of edges found: %d", len(edges))
                
                if not edges:
                    logger.info("No more products found")
                    break
                
                # Process products
                batch_products = []
                for edge in edges:
                    node = edge.get('node', {})
                    if not node:
                        logger.debug("Skipping empty node")
                        continue
                    
                    # Check if product has category when uncategorized flag is set
                    if uncategorized:
                        product_category = node.get('productCategory', {})
                        if product_category and product_category.get('productTaxonomyNode'):
                            logger.debug(f"Skipping categorized product: {node.get('title')} (Category: {product_category['productTaxonomyNode'].get('fullName')})")
                            continue
                        logger.debug(f"Found uncategorized product: {node.get('title')}")
                    
                    # Create product object
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
                    
                    batch_products.append(product)
                    logger.debug(f"Added product: {product['title']} ({product['status']})")
                
                # Log batch results
                logger.info(f"Found {len(batch_products)} matching products out of {len(edges)} total")
                
                # Add batch products to all_products
                all_products.extend(batch_products)
                
                if len(all_products) >= limit:
                    logger.debug("Reached product limit")
                    break
                
                # Update pagination
                page_info = products_data.get('pageInfo', {})
                if not page_info.get('hasNextPage'):
                    logger.debug("No more pages available")
                    break
                cursor = page_info.get('endCursor')
                
                logger.info(f"Fetched {len(all_products)}/{limit} products")
                
                # Add small delay between requests
                time.sleep(0.5)
            
            logger.info(f"Successfully fetched {len(all_products)} products")
            return all_products[:limit]
            
        except Exception as e:
            logger.error(f"Failed to fetch products: {str(e)}")
            return []

    def _format_metafields(self, product_id: str, attributes: Dict[str, Union[str, List[str]]]) -> List[Dict]:
        """Format metafields for GraphQL mutation"""
        metafields = []
        
        # Skip if no attributes
        if not attributes:
            logger.warning(f"No attributes to format for product {product_id}")
            return []

        # Skip category key
        category_info = attributes.pop('category', None)
        if not category_info:
            logger.warning(f"No category info found for product {product_id}")
            return []

        # Format each attribute as a metafield
        for attr_id, values in attributes.items():
            # Skip non-attribute IDs
            if not isinstance(attr_id, str) or not attr_id.startswith('gid://'):
                logger.debug(f"Skipping non-attribute key: {attr_id}")
                continue
            
            # Get attribute handle
            attr_handle = self.enricher.mapper.get_handle_from_attribute_id(attr_id)
            if not attr_handle:
                logger.debug(f"No handle found for attribute {attr_id}")
                continue
            
            # Handle single value or list of values
            if isinstance(values, list):
                # Get metaobject GIDs for all values
                metaobject_gids = []
                for value_id in values:
                    gid = self.enricher.mapper.get_metaobject_gid(value_id)
                    if gid:
                        metaobject_gids.append(gid)
                        logger.debug(f"Found metaobject GID for {value_id}: {gid}")
                    else:
                        logger.warning(f"No metaobject GID found for value {value_id}")
                
                if metaobject_gids:
                    metafields.append({
                        'ownerId': product_id,
                        'key': attr_handle,
                        'value': json.dumps(metaobject_gids),
                        'type': 'list.metaobject_reference',
                        'namespace': 'shopify'
                    })
            else:
                # Single value
                gid = self.enricher.mapper.get_metaobject_gid(values)
                if gid:
                    metafields.append({
                        'ownerId': product_id,
                        'key': attr_handle,
                        'value': json.dumps([gid]),
                        'type': 'list.metaobject_reference',
                        'namespace': 'shopify'
                    })
                else:
                    logger.warning(f"No metaobject GID found for value {values}")
        
        logger.debug(f"Formatted {len(metafields)} metafields for product {product_id}")
        return metafields

    def _update_product(self, product_id: str, category_id: str, metafields: List[Dict]) -> bool:
        """Update product with category and metafields in Shopify"""
        try:
            success = True  # Track overall success
            
            # First update category
            category_variables = {
                "input": {
                    "id": product_id,
                    "category": category_id
                }
            }
            
            category_response = self.client.execute_query(
                self.UPDATE_PRODUCT_CATEGORY_MUTATION,
                variables=category_variables
            )
            
            if 'errors' in category_response:
                logger.error(f"Category update failed: {category_response['errors']}")
                return False

            # Then update metafields
            if metafields:
                metafield_variables = {
                    "metafields": metafields
                }
                
                logger.debug(f"Updating metafields: {json.dumps(metafield_variables, indent=2)}")
                
                metafield_response = self.client.execute_query(
                    self.UPDATE_PRODUCT_METAFIELDS_MUTATION,
                    variables=metafield_variables
                )
                
                # Check for API errors
                if 'errors' in metafield_response:
                    logger.error(f"Metafields update failed with API errors: {metafield_response['errors']}")
                    success = False
                elif 'metafieldsSet' not in metafield_response:
                    logger.error("Invalid metafield response format - missing metafieldsSet")
                    logger.debug(f"Response: {json.dumps(metafield_response, indent=2)}")
                    success = False
                else:
                    metafields_set = metafield_response['metafieldsSet']
                    
                    # Check for user errors
                    user_errors = metafields_set.get('userErrors', [])
                    if user_errors:
                        logger.error("Metafields update failed with user errors:")
                        for error in user_errors:
                            logger.error(f"  Field: {error.get('field')}")
                            logger.error(f"  Message: {error.get('message')}")
                        success = False
                    else:
                        # Log successful updates
                        updated = metafields_set.get('metafields', [])
                        logger.info(f"Successfully updated {len(updated)} metafields")
                        
                        # Debug log the updated metafields
                        for metafield in updated:
                            logger.debug(f"Updated metafield: {metafield['key']} = {metafield['value']}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update product {product_id}: {str(e)}")
            return False

    def write_low_confidence_report(self, results: List[Dict], threshold: float = 0.7):
        """Write low confidence matches to CSV"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"low_confidence_matches_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow([
                'Product ID', 
                'Title', 
                'Category', 
                'Confidence',
                'Attributes'
            ])
            
            # Write low confidence matches
            for result in results:
                if result.get('confidence', 0) < threshold:
                    writer.writerow([
                        result['product_id'],
                        result['title'],
                        result['category'],
                        result.get('confidence', 0),
                        result.get('attributes', 'None')
                    ])
            
            logger.info(f"Low confidence report written to {filename}")

    def test_enrichment(self, products: List[Dict], perform_updates: bool = False):
        """Test enrichment for products"""
        results = []
        
        for product in products:
            try:
                # Get product details
                product_id = product['product_id']
                title = product['title']
                
                logger.info(f"Processing product: {title}")
                
                # Get enriched data
                enriched = self.enricher.enrich_product(product)
                if not enriched:
                    logger.warning(f"No enrichment data for product: {title}")
                    results.append({
                        'product_id': product_id,
                        'title': title,
                        'status': 'Failed - No enrichment data'
                    })
                    continue  # Continue to next product instead of returning
                
                # Get category and confidence
                category_id, confidence = self.enricher.categorizer.categorize(
                    title,
                    product.get('description', '')
                )
                
                # Get attributes
                attributes = self.enricher.get_product_attributes(product)
                
                # Format metafields
                metafields = self._format_metafields(product_id, attributes.copy())
                
                # Perform updates if requested
                update_status = 'Not Attempted'
                if perform_updates and category_id:
                    success = self._update_product(product_id, category_id, metafields)
                    update_status = 'Updated' if success else 'Update Failed'
                
                # Format result
                result = {
                    'product_id': product_id,
                    'title': title,
                    'category': self.enricher.categorizer.mapper.get_path_from_category_id(category_id) if category_id else 'N/A',
                    'confidence': confidence,
                    'attributes': self._format_attributes_display(attributes),
                    'metafields': metafields,
                    'status': update_status if perform_updates else ('Success' if category_id else 'No matches found')
                }
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error processing product {product.get('title', 'Unknown')}: {str(e)}")
                results.append({
                    'product_id': product.get('product_id', 'Unknown'),
                    'title': product.get('title', 'Unknown'),
                    'status': f'Failed - {str(e)}'
                })
                continue  # Continue to next product
        
        # Write low confidence report
        self.write_low_confidence_report(results)
        
        # Print results table
        self._print_results_table(results)
        return results

    def _print_results_table(self, results: List[Dict]) -> None:
        """Print results in a formatted table"""
        # Create results table
        table = Table(title="Enrichment Test Results")
        table.add_column("Product ID", style="cyan")
        table.add_column("Title", style="blue")
        table.add_column("Category", style="green")
        table.add_column("Confidence", style="yellow")
        table.add_column("Attributes", style="magenta")
        table.add_column("Metafields", style="magenta")
        table.add_column("Status", style="red")
        
        # Track success/failure counts
        success_count = sum(1 for r in results if r['status'] == 'Success')
        fail_count = len(results) - success_count
        
        # Add rows to table
        for result in results:
            # Format metafields for display
            metafields_display = "\n".join(
                f"{m['key']}: {m['value']}"
                for m in result['metafields']
            ) or "None"
            
            table.add_row(
                result['product_id'],
                result['title'],
                result['category'],
                f"{result['confidence']:.2f}",
                result['attributes'],
                metafields_display,
                result['status']
            )
        
        # Print summary
        console.print("\n")
        console.print(Panel(
            f"Processed {len(results)} products\n"
            f"✅ {success_count} successful\n"
            f"❌ {fail_count} failed",
            title="Summary",
            expand=False
        ))
        
        # Print table
        console.print("\n")
        console.print(table)

    def _format_attributes_display(self, attributes: Dict) -> str:
        """Format attributes for display"""
        if not attributes:
            return "None"
        
        attr_lines = []
        for key, values in attributes.items():
            if key == 'category':
                continue
            
            # Get attribute handle
            attr_handle = self.enricher.mapper.get_handle_from_attribute_id(key)
            if not attr_handle:
                continue
            
            # Get human-readable names for values
            if isinstance(values, list):
                value_names = []
                for value_id in values:
                    value_info = self.enricher.mapper.values.get(value_id, {})
                    value_names.append(value_info.get('name', value_id))
                attr_lines.append(f"{attr_handle}: {', '.join(value_names)}")
            else:
                value_info = self.enricher.mapper.values.get(values, {})
                value_name = value_info.get('name', values)
                attr_lines.append(f"{attr_handle}: {value_name}")
        
        return "\n".join(attr_lines) if attr_lines else "None"

    def _get_category_matches(self, title: str, description: str) -> List[Tuple[str, float]]:
        """Get all matching categories with confidence scores"""
        title = title.lower()
        description = description.lower()
        matches = []

        # Super clear indicators with massive weights
        clear_indicators = {
            # ... existing indicators ...
            
            'Coats & Jackets': {
                'terms': ['jacket', 'coat', 'blazer', 'rider jacket', 'worker jacket', 'corduroy jacket'],
                'excludes': ['dress', 'set'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Outerwear > Coats & Jackets'
            },
            
            'Shirts': {
                'terms': ['flannel shirt', 'button up shirt', 'button down shirt', 'plaid shirt'],
                'excludes': ['dress', 'set'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Clothing Tops > Shirts'
            },
            
            'Skorts': {
                'terms': ['skort'],
                'excludes': ['set'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Shorts'
            },
            
            # ... rest of the indicators ...
        }

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
    parser = argparse.ArgumentParser(description='Test product enrichment')
    parser.add_argument('--status', type=str, choices=['draft', 'active'], help='Filter by product status')
    parser.add_argument('--limit', type=int, default=250, help='Maximum number of products to fetch')
    parser.add_argument('--batch-size', type=int, default=50, help='Number of products to process in each batch')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--update', action='store_true', help='Perform updates to Shopify')
    parser.add_argument('--uncategorized', action='store_true', help='Only process products without categories')
    args = parser.parse_args()

    # Validate arguments
    if args.batch_size > args.limit:
        console.print("[red]Error: batch-size cannot be larger than limit[/red]")
        return
    
    if args.batch_size <= 0 or args.limit <= 0:
        console.print("[red]Error: batch-size and limit must be positive numbers[/red]")
        return

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
    
    # Process products in batches
    total_processed = 0
    processed_ids = set()  # Keep track of processed product IDs
    
    while total_processed < args.limit:
        try:
            batch_size = min(args.batch_size, args.limit - total_processed)
            
            # Fetch batch
            console.print(f"\n[yellow]Fetching batch of {batch_size} products...[/yellow]")
            products = tester.fetch_recent_products(
                limit=batch_size,
                status=args.status,
                uncategorized=args.uncategorized
            )
            
            if not products:
                console.print("[yellow]No more products found[/yellow]")
                break
            
            # Filter out already processed products
            new_products = [p for p in products if p['product_id'] not in processed_ids]
            
            if not new_products:
                console.print("[yellow]No new products to process[/yellow]")
                break
                
            # Process and update batch
            console.print(f"\n[green]Processing batch of {len(new_products)} products...[/green]")
            
            # Split updates into smaller chunks to avoid rate limits
            update_chunk_size = min(10, len(new_products))  # Process max 10 updates at a time
            for i in range(0, len(new_products), update_chunk_size):
                chunk = new_products[i:i + update_chunk_size]
                console.print(f"\n[blue]Updating products {i+1} to {i+len(chunk)} in current batch...[/blue]")
                
                try:
                    tester.test_enrichment(chunk, perform_updates=args.update)
                    # Add processed products to tracking set
                    for product in chunk:
                        processed_ids.add(product['product_id'])
                    # Small delay between update chunks
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error processing update chunk: {str(e)}")
                    console.print(f"[red]Error updating products {i+1} to {i+len(chunk)}: {str(e)}[/red]")
                    continue
            
            total_processed += len(new_products)
            console.print(f"\n[blue]Total products processed: {total_processed}/{min(args.limit, len(processed_ids))}[/blue]")
            
            # If we've processed all available products, break
            if len(new_products) < batch_size:
                console.print("[yellow]All available products have been processed[/yellow]")
                break
                
            # Add delay between batches to avoid rate limits
            if total_processed < args.limit:
                console.print("[yellow]Waiting 2 seconds before next batch...[/yellow]")
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            console.print(f"[red]Error processing batch: {str(e)}[/red]")
            break

    console.print(f"\n[green]Finished processing {total_processed} products[/green]")

if __name__ == "__main__":
    main()
