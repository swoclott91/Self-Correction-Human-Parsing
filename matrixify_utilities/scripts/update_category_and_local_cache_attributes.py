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
from datetime import datetime

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

# Add after other constants
GID_CACHE_FILE = Path("matrixify_utilities/metaobject_sync/gid_cache.json")

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
            validate_schema=False
        )
        self.enricher = ProductEnricher(
            taxonomy_dir=taxonomy_dir,
            confidence_threshold=0.5
        )
        self.debug_mode = debug_mode
        
        # Load the GID cache
        try:
            with open(GID_CACHE_FILE, 'r') as f:
                self.gid_cache = json.load(f)
            logger.info(f"Loaded GID cache with {len(self.gid_cache)} attribute types")
        except Exception as e:
            logger.error(f"Failed to load GID cache: {e}")
            self.gid_cache = {}
        
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

    def _resolve_metafield_value(self, field: Dict) -> Optional[str]:
        """Map taxonomy value to metaobject GID using local cache"""
        try:
            key = field['key']  # e.g. 'fabric'
            taxonomy_value = field['value']  # e.g. 'gid://shopify/TaxonomyValue/16996'
            
            logger.debug(f"Looking up metaobject GID for {key} taxonomy value: {taxonomy_value}")
            
            # Get the taxonomy ID number
            taxonomy_id = taxonomy_value.split('/')[-1]  # e.g. '16996'
            
            # Get the mapping from the enricher's taxonomy mapper
            handle = self.enricher.mapper.get_handle_for_taxonomy_id(key, taxonomy_id)
            if not handle:
                logger.warning(f"Could not find handle for {key} taxonomy ID {taxonomy_id}")
                return None
            
            logger.debug(f"Mapped taxonomy ID {taxonomy_id} to handle: {handle}")
            
            # Look up the metaobject GID in our cache
            if key in self.gid_cache and handle in self.gid_cache[key]:
                metaobject_gid = self.gid_cache[key][handle]
                logger.debug(f"✅ Found metaobject GID in cache: {metaobject_gid}")
                return metaobject_gid
            else:
                logger.warning(f"No cache entry found for {key}/{handle}")
                return None

        except Exception as e:
            logger.error(f"Error resolving metafield value: {str(e)}")
            return None

    def _update_product(self, product_id: str, category_id: str, metafields: List[Dict]) -> bool:
        """Update product with category and metafields"""
        try:
            # Update category first
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

            # Then process and update metafields separately
            processed_metafields = []
            for field in metafields:
                logger.debug(f"\nProcessing metafield: {json.dumps(field, indent=2)}")
                
                metaobject_gid = self._resolve_metafield_value(field)
                if metaobject_gid:
                    processed_field = {
                        "ownerId": product_id,
                        "namespace": "shopify",
                        "key": field["key"],
                        "type": "list.metaobject_reference",
                        "value": json.dumps([metaobject_gid])  # Must be JSON string array
                    }
                    processed_metafields.append(processed_field)
                    logger.debug(f"✅ Processed metafield: {json.dumps(processed_field, indent=2)}")
                else:
                    logger.warning(f"❌ Could not resolve GID for {field['key']}/{field['value']}")

            # Update metafields if we have any
            if processed_metafields:
                metafield_variables = {
                    "metafields": processed_metafields
                }
                
                logger.debug(f"Updating metafields with payload:\n{json.dumps(metafield_variables, indent=2)}")
                
                metafield_response = self.client.execute_query(
                    """
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
                    """,
                    variables=metafield_variables
                )
                
                if 'errors' in metafield_response or (
                    'data' in metafield_response and 
                    'metafieldsSet' in metafield_response['data'] and 
                    metafield_response['data']['metafieldsSet'].get('userErrors')
                ):
                    errors = metafield_response.get('errors') or metafield_response['data']['metafieldsSet'].get('userErrors')
                    logger.error(f"Metafields update failed: {errors}")
                    return False
                
                logger.info(f"Successfully updated {len(processed_metafields)} metafields")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update product {product_id}: {str(e)}")
            return False

    def test_enrichment(self, products: List[Dict]):
        """Test enrichment pipeline with products"""
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

            # 1. Update category
            category_response = self.client.execute_query(
                self.UPDATE_PRODUCT_CATEGORY_MUTATION,
                variables={
                    "input": {
                        "id": product_id,
                        "category": category_id
                    }
                }
            )

            if 'errors' in category_response:
                logger.error(f"[❌] Failed to update category for product {product_id}: {category_response['errors']}")
                table.add_row(product_id, product['title'], "-", "-", "-", "[red]Category Failed[/red]")
                continue

            # 2. Resolve and update metafields
            metafields = []
            for field in payload.get('metafields', []):
                # Extract taxonomy value ID from the value field
                taxonomy_value_id = field['value'].split('/')[-1]
                
                logger.debug(f"Processing metafield: key={field['key']}, taxonomy_value_id={taxonomy_value_id}")
                logger.debug(f"Metaobject resolver methods: {dir(self.metaobject_resolver)}")
                
                # Get metaobject GID
                try:
                    logger.debug(f"Attempting to resolve GID with resolve_gid method")
                    logger.debug(f"Arguments: taxonomy_value_id={taxonomy_value_id}, attribute_handle={field['key']}")
                    
                    metaobject_gid = self.metaobject_resolver.resolve_gid(
                        taxonomy_value_id=taxonomy_value_id,
                        attribute_handle=field['key']
                    )
                    
                    logger.debug(f"Resolved GID result: {metaobject_gid}")
                    
                    if metaobject_gid:
                        metafields.append({
                            "ownerId": product_id,
                            "namespace": "shopify",
                            "key": field["key"],
                            "value": metaobject_gid,
                            "type": "metaobject_reference"
                        })
                        logger.debug(f"Added metafield: {field['key']} -> {metaobject_gid}")
                    else:
                        logger.warning(f"Could not resolve metaobject GID for {field['key']}")
                except Exception as e:
                    logger.error(f"Error resolving metaobject GID for {field['key']}: {str(e)}")
                    logger.error(f"Stack trace:", exc_info=True)
                    continue

            if metafields:
                metafield_response = self.client.execute_query(
                    self.UPDATE_PRODUCT_METAFIELDS_MUTATION,
                    variables={"metafields": metafields}
                )

                if "errors" in metafield_response:
                    logger.error(f"[❌] Failed to update metafields for {product_id}: {metafield_response['errors']}")
                    table.add_row(product_id, product['title'], "-", "-", "-", "[red]Metafields Failed[/red]")
                    continue

            # 3. Display output
            category_path = self.enricher.mapper.get_path_from_category_id(category_id)
            _, confidence = self.enricher.categorizer.categorize(product['title'])
            
            attr_lines = []
            for field in metafields:
                attr_lines.append(f"{field['key']}: {field['value']}")
            attr_display = "\n".join(attr_lines) if attr_lines else "-"

            table.add_row(
                product_id,
                product['title'],
                category_path,
                f"{confidence:.2f}",
                attr_display,
                "[green]Success[/green]"
            )

        # Add failed results to table
        for result in failed:
            product_id = result['product_id']
            product = next(p for p in products if p['product_id'] == product_id)
            
            table.add_row(
                product_id,
                product['title'],
                "Failed",
                "-",
                str(result.get('errors', [])),
                "[red]Failed[/red]"
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

    def format_graphql_payload(self, result: Dict) -> Dict:
        """Format enrichment result for GraphQL update"""
        if not result.get('category', {}).get('gid'):
            return None
        
        # Only include category in the initial update
        payload = {
            "id": result['product_id'],
            "category": result['category']['gid']
        }
        
        # Log the metafields for reference but don't include in payload
        metafields = []
        for attr_id, value in result.items():
            if attr_id != 'category' and isinstance(attr_id, str) and attr_id.startswith('gid://'):
                key = self.enricher.mapper.get_attribute_handle(attr_id)
                if key:
                    metafields.append({
                        "namespace": "standard",
                        "key": key,
                        "value": value,
                        "type": "single_line_text_field"
                    })
        
        if metafields:
            logger.info("Taxonomy attributes for future API support: " + 
                       json.dumps(metafields, indent=2))
        
        return payload

def main():
    """Update local cache of categories and attributes"""
    # Initialize API client
    client = ShopifyClient()
    
    # Get taxonomy data
    categories = get_taxonomy_categories(client)
    attributes = get_taxonomy_attributes(client)
    values = get_taxonomy_values(client)
    
    # Save to files
    taxonomy_dir = Path(__file__).parent.parent / 'taxonomy_data'
    taxonomy_dir.mkdir(exist_ok=True)
    
    with open(taxonomy_dir / 'categories.json', 'w') as f:
        json.dump({'version': '1.0', 'updated_at': datetime.now().isoformat(), 'data': categories}, f, indent=2)
        
    with open(taxonomy_dir / 'attributes.json', 'w') as f:
        json.dump({'version': '1.0', 'updated_at': datetime.now().isoformat(), 'data': attributes}, f, indent=2)
        
    with open(taxonomy_dir / 'values.json', 'w') as f:
        json.dump({'version': '1.0', 'updated_at': datetime.now().isoformat(), 'data': values}, f, indent=2)
        
    print(f"Updated taxonomy data in {taxonomy_dir}")
    print(f"Categories: {len(categories)}")
    print(f"Attributes: {len(attributes)}")
    print(f"Values: {len(values)}")

if __name__ == "__main__":
    main()
