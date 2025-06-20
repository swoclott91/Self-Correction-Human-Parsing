import os
import logging
from typing import Optional, Dict, List, Generator, Tuple, Any
from pathlib import Path
from datetime import datetime
import json
from tenacity import retry, stop_after_attempt, wait_exponential
import requests
import base64
from .taxonomy import TaxonomyHelper
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

logger = logging.getLogger(__name__)

class ShopifyClient:
    def __init__(self, shop_url: str, access_token: str, validate_schema: bool = True):
        """Initialize the Shopify API client"""
        self.shop_url = shop_url
        self.access_token = access_token
        
        transport = RequestsHTTPTransport(
            url=f'https://{shop_url}/admin/api/2025-04/graphql.json',
            headers={'X-Shopify-Access-Token': access_token},
            verify=True,
        )
        
        self.client = Client(
            transport=transport,
            fetch_schema_from_transport=validate_schema
        )
        
        # Set up base URLs with latest API version
        api_version = '2025-04'  # Update to latest version
        self.rest_url = f"https://{self.shop_url}/admin/api/{api_version}"
        self.graphql_url = f"https://{self.shop_url}/admin/api/{api_version}/graphql.json"
        
        # Initialize session with authentication
        self.session = requests.Session()
        self.session.headers.update({
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        })
        
        logger.info(f"Initialized Shopify API client for {self.shop_url}")
        self.taxonomy_helper = TaxonomyHelper()

    def setup_session(self):
        """Configure Shopify API session"""
        api_version = '2025-04'  # Update as needed
        shop_url = f"https://{self.shop_url}/admin/api/{api_version}/graphql.json"
        
        try:
            self.session = requests.Session()
            self.session.headers.update({
                'X-Shopify-Access-Token': self.access_token,
                'Content-Type': 'application/json'
            })
            logger.info(f"Initialized Shopify API client for {self.shop_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Shopify session: {e}")
            raise

    def execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query against the Shopify Admin API
        
        Args:
            query: GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            Dict containing the query response
            
        Raises:
            Exception: If the query fails or returns errors
        """
        try:
            # Parse the query string
            gql_query = gql(query)
            
            # Execute the query
            result = self.client.execute(
                gql_query,
                variable_values=variables
            )
            
            return result
            
        except Exception as e:
            logger.error(f"GraphQL query failed: {str(e)}")
            raise

    def execute_mutation(self, mutation: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL mutation against the Shopify Admin API
        
        Args:
            mutation: GraphQL mutation string
            variables: Optional variables for the mutation
            
        Returns:
            Dict containing the mutation response
        """
        return self.execute_query(mutation, variables)

    def test_connection(self) -> bool:
        """Test the API connection with a simple query"""
        test_query = """
        query {
          shop {
            name
          }
        }
        """
        
        try:
            result = self.execute_query(test_query)
            shop_name = result.get('shop', {}).get('name')
            logger.info(f"Successfully connected to shop: {shop_name}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    def create_metaobjects_batch(self, definition_type: str, metaobjects: List[Dict]) -> List[str]:
        """Create metaobjects using GraphQL mutation, skipping existing ones"""
        created_handles = []
        skipped_handles = []
        
        mutation = """
        mutation metaobjectCreate($metaobject: MetaobjectCreateInput!) {
            metaobjectCreate(metaobject: $metaobject) {
                metaobject {
                    handle
                }
                userErrors {
                    field
                    message
                    code
                }
            }
        }
        """
        
        for metaobject in metaobjects:
            handle = metaobject["handle"]
            
            # Skip if metaobject already exists
            if self.validate_metaobject(definition_type, handle):
                logger.info(f"Skipping existing metaobject: {handle}")
                skipped_handles.append(handle)
                continue
            
            # Adjust fields based on their types
            adjusted_fields = []
            for field in metaobject["fields"]:
                if field["key"] == "color_taxonomy_reference":
                    adjusted_fields.append({
                        "key": field["key"],
                        "value": json.dumps([field["value"]])
                    })
                elif field["key"] == "pattern_taxonomy_reference":
                    adjusted_fields.append({
                        "key": field["key"],
                        "value": field["value"]
                    })
                else:
                    adjusted_fields.append(field)
            
            variables = {
                "metaobject": {
                    "type": definition_type,
                    "handle": handle,
                    "fields": adjusted_fields
                }
            }
            
            try:
                result = self.execute_mutation(mutation, variables)
                logger.debug(f"API Request: {json.dumps(variables, indent=2)}")
                logger.debug(f"API Response: {json.dumps(result, indent=2)}")
                
                if 'data' in result and 'metaobjectCreate' in result['data']:
                    response = result['data']['metaobjectCreate']
                    
                    if response.get('userErrors'):
                        for error in response['userErrors']:
                            logger.error(f"Error creating metaobject {handle}: {error['message']}")
                        continue
                        
                    if response.get('metaobject', {}).get('handle'):
                        created_handles.append(response['metaobject']['handle'])
                        logger.info(f"Created metaobject: {response['metaobject']['handle']}")
                        
            except Exception as e:
                logger.error(f"Failed to create metaobject {handle}: {e}")
                
        return created_handles, skipped_handles

    def validate_metaobject(self, definition_type: str, handle: str) -> bool:
        """Check if a metaobject exists using GraphQL query"""
        # Strip any numeric suffix from handle (e.g., "blue-d5dfe7-2" -> "blue-d5dfe7")
        base_handle = handle.split('-')
        if base_handle[-1].isdigit():
            base_handle = base_handle[:-1]
        base_handle = '-'.join(base_handle)
        
        query = """
        query getMetaobjects($type: String!) {
            metaobjects(type: $type, first: 100) {
                nodes {
                    handle
                    fields {
                        key
                        value
                    }
                }
            }
        }
        """
        
        try:
            result = self.execute_query(query, {
                "type": definition_type
            })
            
            if not result or 'data' not in result:
                return False
            
            metaobjects = result.get('data', {}).get('metaobjects', {}).get('nodes', [])
            
            # Check if any existing metaobject handle starts with our base handle
            for metaobject in metaobjects:
                existing_handle = metaobject['handle']
                if existing_handle.startswith(base_handle):
                    logger.debug(f"Found existing metaobject: {existing_handle} matches {base_handle}")
                    return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error validating metaobject {handle}: {e}")
            return False

    def get_metaobject_definitions(self) -> List[Dict]:
        """Get all metaobject definitions using GraphQL query"""
        query = """
        {
            metaobjectDefinitions(first: 50) {
                nodes {
                    id
                    type
                    name
                    fieldDefinitions {
                        name
                        key
                        type {
                            name
                        }
                    }
                }
            }
        }
        """
        
        try:
            result = self.execute_query(query)
            if not result or 'data' not in result:
                logger.error(f"Unexpected API response: {result}")
                return []
            
            definitions = result.get('data', {}).get('metaobjectDefinitions', {}).get('nodes', [])
            
            # Log found definitions
            if definitions:
                logger.info(f"Found {len(definitions)} metaobject definitions")
                for definition in definitions:
                    logger.debug(f"Definition: {definition['type']} ({definition['name']})")
            else:
                logger.warning("No metaobject definitions found")
            
            return definitions
        
        except Exception as e:
            logger.error(f"Error fetching metaobject definitions: {e}")
            return []

    def update_product_metafields(self, product_id: int, metafields: List[Dict]) -> bool:
        """Update product metafields"""
        try:
            product = shopify.Product.find(product_id)
            for metafield in metafields:
                product.add_metafield(shopify.Metafield(metafield))
            return product.save()
        except Exception as e:
            logger.error(f"Error updating metafields for product {product_id}: {e}")
            return False
            
    def get_products_batch(self, batch_size: int = 50) -> Generator[List[Dict], None, None]:
        """Get all products in batches using GraphQL"""
        query = """
        query getProducts($cursor: String, $pageSize: Int!) {
            products(first: $pageSize, after: $cursor) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    id
                    title
                    handle
                    options {
                        name
                        values
                    }
                    variants(first: 100) {
                        nodes {
                            id
                            title
                            image {
                                url
                            }
                            selectedOptions {
                                name
                                value
                            }
                        }
                    }
                }
            }
        }
        """
        
        try:
            cursor = None
            while True:
                result = self.execute_query(query, {
                    "pageSize": batch_size,
                    "cursor": cursor
                })
                
                if not result or 'data' not in result:
                    break
                    
                products = result['data']['products']['nodes']
                if not products:
                    break
                    
                yield products
                
                # Check if there are more pages
                page_info = result['data']['products']['pageInfo']
                if not page_info['hasNextPage']:
                    break
                    
                cursor = page_info['endCursor']
                
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            raise

    def inspect_product_metafields(self, product_id: str) -> Dict:
        """Inspect a product's metafields and variant connections"""
        query = """
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                handle
                title
                metafields(first: 100) {
                    nodes {
                        id
                        namespace
                        key
                        value
                        type
                        definition {
                            id
                            name
                        }
                    }
                }
                variants(first: 100) {
                    nodes {
                        id
                        title
                        selectedOptions {
                            name
                            value
                        }
                        metafields(first: 100) {
                            nodes {
                                id
                                namespace
                                key
                                value
                                type
                                definition {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        try:
            result = self.execute_query(query, {
                "id": product_id
            })
            
            if result.get('data', {}).get('product'):
                logger.debug(f"Product inspection result: {json.dumps(result['data']['product'], indent=2)}")
                return result['data']['product']
            else:
                logger.error(f"Failed to get product: {result}")
                return None
            
        except Exception as e:
            logger.error(f"Error inspecting product: {e}")
            return None

    def get_metafield_definitions(self, namespace: str = None, owner_type: str = "PRODUCTVARIANT") -> List[Dict]:
        """Get metafield definitions filtered by namespace and/or owner type"""
        query = """
        query getMetafieldDefinitions($namespace: String, $ownerType: MetafieldOwnerType!) {
            metafieldDefinitions(
                first: 100,
                namespace: $namespace,
                ownerType: $ownerType
            ) {
                nodes {
                    id
                    name
                    key
                    namespace
                    type {
                        name
                    }
                    ownerType
                    validations {
                        name
                        value
                    }
                }
            }
        }
        """
        
        try:
            result = self.execute_query(query, {
                "namespace": namespace,
                "ownerType": owner_type
            })
            
            if result.get('data', {}).get('metafieldDefinitions', {}).get('nodes'):
                definitions = result['data']['metafieldDefinitions']['nodes']
                logger.debug(f"Found {len(definitions)} metafield definitions")
                return definitions
            else:
                logger.error(f"Failed to get metafield definitions: {result}")
                return []
            
        except Exception as e:
            logger.error(f"Error getting metafield definitions: {e}")
            return []

    def connect_variant_to_metafield(
        self, 
        variant_id: str, 
        definition_id: str,
        value: str
    ) -> bool:
        """Connect a variant option to a metafield definition"""
        mutation = """
        mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
            metafieldsSet(metafields: $metafields) {
                metafields {
                    id
                    key
                    namespace
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "metafields": [{
                "ownerId": variant_id,
                "type": "metaobject_reference",
                "value": value,
                "definitionId": definition_id
            }]
        }
        
        try:
            result = self.execute_mutation(mutation, variables)
            
            if result.get('data', {}).get('metafieldsSet', {}).get('userErrors'):
                errors = result['data']['metafieldsSet']['userErrors']
                for error in errors:
                    logger.error(f"Failed to connect variant: {error['message']}")
                return False
            
            logger.info(f"Successfully connected variant {variant_id} to metafield")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting variant: {e}")
            return False

    def connect_variant_color(self, variant_id: str, color_metaobject_id: str) -> bool:
        """Connect a variant's color option to the corresponding color metaobject"""
        
        # First create the palette metafield
        palette_result = self.connect_variant_to_metafield(
            variant_id=variant_id,
            definition_id="gid://shopify/MetafieldDefinition/87458021748",  # Palette definition
            value=color_metaobject_id
        )
        
        if not palette_result:
            return False
        
        return True

    def connect_product_color(self, product_id: str, color_metaobject_id: str) -> bool:
        """Connect a product's color to the corresponding color metaobject"""
        
        mutation = """
        mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
            metafieldsSet(metafields: $metafields) {
                metafields {
                    id
                    key
                    namespace
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "metafields": [{
                "ownerId": product_id,
                "type": "list.metaobject_reference",
                "value": json.dumps([color_metaobject_id]),
                "definitionId": "gid://shopify/MetafieldDefinition/87299490164"  # Color definition
            }]
        }
        
        try:
            result = self.execute_mutation(mutation, variables)
            
            if result.get('data', {}).get('metafieldsSet', {}).get('userErrors'):
                errors = result['data']['metafieldsSet']['userErrors']
                for error in errors:
                    logger.error(f"Failed to connect product color: {error['message']}")
                return False
            
            logger.info(f"Successfully connected product {product_id} to color {color_metaobject_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting product color: {e}")
            return False

    def bulk_connect_product_colors(self, product_color_map: Dict[str, str]) -> Tuple[int, int]:
        """Connect multiple products and their variants to color metaobjects
        
        Args:
            product_color_map: Dict mapping product IDs to color metaobject IDs
        
        Returns:
            Tuple of (success_count, error_count)
        """
        success_count = 0
        error_count = 0
        
        for product_id, color_id in product_color_map.items():
            try:
                # Get product details
                product = self.inspect_product_metafields(product_id)
                if not product:
                    logger.error(f"Failed to get product {product_id}")
                    error_count += 1
                    continue
                    
                # Connect product to color
                if not self.connect_product_color(product_id, color_id):
                    logger.error(f"Failed to connect product {product_id} to color {color_id}")
                    error_count += 1
                    continue
                    
                # Connect variants
                variant_errors = False
                for variant in product['variants']['nodes']:
                    color_option = next((opt for opt in variant['selectedOptions'] 
                                       if opt['name'].lower() == 'color'), None)
                    if color_option:
                        if not self.connect_variant_color(variant['id'], color_id):
                            logger.error(f"Failed to connect variant {variant['id']}")
                            variant_errors = True
                            break
                            
                if variant_errors:
                    error_count += 1
                    continue
                    
                success_count += 1
                
            except Exception as e:
                logger.error(f"Error processing product {product_id}: {e}")
                error_count += 1
                
        return success_count, error_count

    def get_color_metaobject_id(self, color_handle: str) -> Optional[str]:
        """Get metaobject ID for a color handle"""
        query = """
        query getMetaobject($type: String!, $handle: String!) {
            metaobjects(type: $type, first: 1, handles: [$handle]) {
                nodes {
                    id
                    handle
                }
            }
        }
        """
        
        try:
            result = self.execute_query(query, {
                "type": "shopify--color-pattern",  # Using full type name
                "handle": color_handle
            })
            
            nodes = result.get('data', {}).get('metaobjects', {}).get('nodes', [])
            if nodes:
                return nodes[0]['id']
            return None
            
        except Exception as e:
            logger.error(f"Error getting color metaobject ID for {color_handle}: {e}")
            return None

    def get_product(self, product_id: str) -> Optional[Dict]:
        """Get product details from Shopify"""
        try:
            response = self.session.get(f"{self.rest_url}/products/{product_id}.json")
            response.raise_for_status()
            return response.json()['product']
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            return None

    def get_product_category(self, product_id: str) -> Optional[str]:
        """Get a product's current category"""
        query = """
        query($id: ID!) {
            product(id: $id) {
                id
                handle
                title
                metafields(first: 10) {
                    nodes {
                        key
                        namespace
                        value
                    }
                }
            }
        }
        """
        
        try:
            result = self.execute_query(query, {"id": product_id})
            product = result.get('data', {}).get('product', {})
            
            # Find category metafield
            metafields = product.get('metafields', {}).get('nodes', [])
            category_field = next(
                (m for m in metafields 
                 if m.get('namespace') == 'custom' and m.get('key') == 'category'),
                None
            )
            
            return category_field.get('value') if category_field else None
            
        except Exception as e:
            logger.error(f"Error getting product category: {e}")
            return None

    def get_shopify_taxonomy(self) -> List[Dict]:
        """Get Shopify's standard product taxonomy"""
        query = """
        query {
            shop {
                primaryDomain {
                    url
                }
                productTypes(first: 250) {
                    nodes {
                        name
                    }
                }
                products(first: 250) {
                    nodes {
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
            }
        }
        """
        
        try:
            result = self.execute_query(query)
            logger.debug(f"Taxonomy lookup result: {result}")
            
            # Get both product types and taxonomy nodes
            product_types = result.get('data', {}).get('shop', {}).get('productTypes', {}).get('nodes', [])
            products = result.get('data', {}).get('shop', {}).get('products', {}).get('nodes', [])
            
            # Extract unique taxonomy nodes from products
            taxonomy_nodes = {}
            for product in products:
                category = product.get('productCategory', {}).get('productTaxonomyNode', {})
                if category and category.get('id'):
                    taxonomy_nodes[category['id']] = {
                        'id': category['id'],
                        'name': category['name'],
                        'fullName': category['fullName']
                    }
            
            # Combine both into a structured hierarchy
            root = {
                'id': 'root',
                'name': 'All Categories',
                'fullName': 'All Categories',
                'children': {
                    'nodes': [
                        *[{'id': f'type-{i}', 'name': pt['name'], 'fullName': pt['name']} 
                          for i, pt in enumerate(product_types)],
                        *list(taxonomy_nodes.values())
                    ]
                }
            }
            
            return root
            
        except Exception as e:
            logger.error(f"Error getting taxonomy: {e}")
            return {}

    def update_product_category(self, product_id: str, category_path: str) -> bool:
        """Update a product's category using Shopify's product taxonomy"""
        # Ensure proper ID format
        if not product_id.startswith('gid://'):
            product_id = f"gid://shopify/Product/{product_id}"
        
        # First, get all product types
        product_types = self.get_shopify_taxonomy()
        
        # Find matching product type
        matching_type = next(
            (pt for pt in product_types if pt['name'] == category_path),
            None
        )
        
        if not matching_type:
            logger.error(f"Could not find product type: {category_path}")
            return False
        
        # Update the product type
        mutation = """
        mutation productUpdate($input: ProductInput!) {
            productUpdate(input: $input) {
                product {
                    id
                    productType
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "input": {
                "id": product_id,
                "productType": category_path
            }
        }
        
        try:
            result = self.execute_mutation(mutation, variables)
            logger.debug(f"Category update result: {result}")
            
            if result.get('data', {}).get('productUpdate', {}).get('userErrors'):
                errors = result['data']['productUpdate']['userErrors']
                for error in errors:
                    logger.error(f"Failed to update category: {error['message']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating product category: {e}")
            return False

    def get_product_parent_category(self, product_id: str) -> Optional[str]:
        """Get a product's parent category from metafields"""
        # Ensure proper ID format
        if not product_id.startswith('gid://'):
            product_id = f"gid://shopify/Product/{product_id}"
        
        query = """
        query getProductParentCategory($id: ID!) {
            product(id: $id) {
                id
                metafields(first: 10) {
                    nodes {
                        namespace
                        key
                        value
                    }
                }
            }
        }
        """
        
        try:
            result = self.execute_query(query, {'id': product_id})
            logger.debug(f"Parent category query result: {result}")
            
            if result and 'data' in result and 'product' in result['data']:
                metafields = result['data']['product'].get('metafields', {}).get('nodes', [])
                # Find the parent category metafield
                parent_field = next(
                    (m for m in metafields 
                     if m.get('namespace') == 'custom' and m.get('key') == 'parent_category'),
                    None
                )
                if parent_field:
                    return parent_field['value']
            return None
            
        except Exception as e:
            logger.error(f"Error getting parent category: {e}")
            return None

    def get_product_child_category(self, product_id: str) -> Optional[str]:
        """Get a product's child category from metafields"""
        # Ensure proper ID format
        if not product_id.startswith('gid://'):
            product_id = f"gid://shopify/Product/{product_id}"
        
        query = """
        query getProductChildCategory($id: ID!) {
            product(id: $id) {
                id
                metafields(first: 10) {
                    nodes {
                        namespace
                        key
                        value
                    }
                }
            }
        }
        """
        
        try:
            result = self.execute_query(query, {'id': product_id})
            logger.debug(f"Child category query result: {result}")
            
            if result and 'data' in result and 'product' in result['data']:
                metafields = result['data']['product'].get('metafields', {}).get('nodes', [])
                # Find the child category metafield
                child_field = next(
                    (m for m in metafields 
                     if m.get('namespace') == 'custom' and m.get('key') == 'child_category'),
                    None
                )
                if child_field:
                    return child_field['value']
            return None
            
        except Exception as e:
            logger.error(f"Error getting child category: {e}")
            return None

    def update_product_parent_category(self, product_id: str, category: str) -> bool:
        """Update a product's parent category metafield"""
        # Ensure proper ID format
        if not product_id.startswith('gid://'):
            product_id = f"gid://shopify/Product/{product_id}"
        
        mutation = """
        mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
            metafieldsSet(metafields: $metafields) {
                metafields {
                    id
                    key
                    namespace
                    value
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "metafields": [{
                "ownerId": product_id,
                "namespace": "custom",
                "key": "parent_category",
                "type": "single_line_text_field",
                "value": category
            }]
        }
        
        try:
            result = self.execute_mutation(mutation, variables)
            logger.debug(f"Update parent category result: {result}")
            
            if result.get('data', {}).get('metafieldsSet', {}).get('userErrors'):
                errors = result['data']['metafieldsSet']['userErrors']
                for error in errors:
                    logger.error(f"Failed to update parent category: {error['message']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating parent category: {e}")
            return False

    def update_product_child_category(self, product_id: str, category: str) -> bool:
        """Update a product's child category metafield"""
        mutation = """
        mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
            metafieldsSet(metafields: $metafields) {
                metafields {
                    id
                    key
                    namespace
                    value
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "metafields": [{
                "ownerId": product_id,
                "namespace": "custom",
                "key": "child_category",
                "type": "single_line_text_field",
                "value": category
            }]
        }
        
        try:
            result = self.execute_mutation(mutation, variables)
            
            if result.get('data', {}).get('metafieldsSet', {}).get('userErrors'):
                errors = result['data']['metafieldsSet']['userErrors']
                for error in errors:
                    logger.error(f"Failed to update child category: {error['message']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating child category: {e}")
            return False

    def update_product_taxonomy(self, product_id: str, taxonomy_id: str) -> bool:
        """Update product's taxonomy ID in Shopify using GraphQL"""
        try:
            # Format product ID if needed
            if not product_id.startswith('gid://'):
                product_gid = f"gid://shopify/Product/{product_id}"
            else:
                product_gid = product_id

            # Get the category details
            category = self.taxonomy_helper.get_category_by_name("Dresses")
            if not category:
                logger.error("Could not find category")
                return False

            # Use the numeric ID from Google's taxonomy
            taxonomy_gid = f"gid://shopify/ProductTaxonomyNode/{category['taxonomy_id']}"

            logger.debug(f"Updating product taxonomy:")
            logger.debug(f"Product ID: {product_gid}")
            logger.debug(f"Category: {category['full_name']}")
            logger.debug(f"Google ID: {category['taxonomy_id']}")
            logger.debug(f"Shopify ID: {category['shopify_id']}")
            logger.debug(f"Final GID: {taxonomy_gid}")

            mutation = """
            mutation productUpdate($input: ProductInput!) {
                productUpdate(input: $input) {
                    product {
                        id
                        title
                        productCategory {
                            productTaxonomyNode {
                                id
                                name
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

            variables = {
                "input": {
                    "id": product_gid,
                    "productCategory": {
                        "productTaxonomyNodeId": taxonomy_gid
                    }
                }
            }

            logger.debug(f"Variables: {json.dumps(variables, indent=2)}")
            result = self.execute_mutation(mutation, variables)
            
            if result.get('errors'):
                logger.error(f"GraphQL error: {result['errors']}")
                return False

            user_errors = result.get('data', {}).get('productUpdate', {}).get('userErrors', [])
            if user_errors:
                for error in user_errors:
                    logger.error(f"User error: {error.get('message')} (Field: {error.get('field')})")
                return False

            updated_product = result.get('data', {}).get('productUpdate', {}).get('product', {})
            if updated_product:
                logger.info(f"Successfully updated taxonomy for product {updated_product.get('title')}")
                logger.info(f"New category: {updated_product.get('productCategory', {}).get('productTaxonomyNode', {})}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error updating taxonomy: {str(e)}")
            return False

    def get_taxonomy_structure(self) -> Dict:
        """Get the full taxonomy structure from Shopify"""
        query = """
        query {
            shop {
                productTypes(first: 250) {
                    edges {
                        node
                    }
                }
                products(first: 250) {
                    nodes {
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
            }
        }
        """
        
        try:
            result = self.execute_query(query)
            logger.debug(f"Full taxonomy structure: {json.dumps(result, indent=2)}")
            
            # Build taxonomy mapping
            taxonomy_map = {}
            
            # Get product types
            product_types = result.get('data', {}).get('shop', {}).get('productTypes', {}).get('edges', [])
            for edge in product_types:
                if edge.get('node'):
                    taxonomy_map[edge['node']] = {
                        'id': f'type_{edge["node"]}',
                        'name': edge['node'],
                        'fullName': edge['node'],
                        'type': 'product_type'
                    }
            
            # Get taxonomy nodes from products
            products = result.get('data', {}).get('shop', {}).get('products', {}).get('nodes', [])
            for product in products:
                category = product.get('productCategory', {}).get('productTaxonomyNode', {})
                if category and category.get('id'):
                    full_path = category.get('fullName', category.get('name', ''))
                    if full_path:
                        taxonomy_map[full_path] = {
                            'id': category['id'].split('/')[-1],
                            'name': category['name'],
                            'fullName': full_path,
                            'type': 'taxonomy_node',
                            'product_type': product.get('productType', '')
                        }
            
            return taxonomy_map
            
        except Exception as e:
            logger.error(f"Error getting taxonomy structure: {e}")
            return {}

    def find_taxonomy_id(self, category_name: str) -> Optional[str]:
        """Find the taxonomy ID for a given category name"""
        taxonomy = self.get_taxonomy_structure()
        
        # Look for exact matches first
        for fullname, details in taxonomy.items():
            if category_name.lower() in fullname.lower():
                logger.info(f"Found category: {fullname} (ID: {details['id']})")
                return details['id']
        
        return None

    def test_taxonomy_update(self, product_id: str) -> bool:
        """Test updating a product's taxonomy with a known valid category"""
        try:
            # First get the product info
            product_query = """
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
            
            result = self.execute_query(product_query, {"id": product_gid})
            if result.get('errors'):
                logger.error(f"Error getting product: {result['errors']}")
                return False
            
            product = result.get('data', {}).get('product', {})
            logger.info(f"Current product type: {product.get('productType')}")
            logger.info(f"Current taxonomy: {product.get('productCategory', {}).get('productTaxonomyNode', {})}")
            
            # Find the correct dresses taxonomy ID
            dresses_id = self.find_taxonomy_id("Dresses")
            if not dresses_id:
                logger.error("Could not find Dresses category in taxonomy")
                return False
            
            dresses_node_id = f"gid://shopify/ProductTaxonomyNode/{dresses_id}"
            logger.info(f"Using Dresses category node: {dresses_node_id}")
            
            # Update the product
            mutation = """
            mutation productUpdate($input: ProductInput!) {
                productUpdate(input: $input) {
                    product {
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
                    userErrors {
                        field
                        message
                    }
                }
            }
            """

            variables = {
                "input": {
                    "id": product_gid,
                    "productType": "Dresses",
                    "productCategory": {
                        "productTaxonomyNodeId": dresses_node_id
                    }
                }
            }

            logger.debug(f"Testing taxonomy update:")
            logger.debug(f"Product ID: {product_gid}")
            logger.debug(f"Variables: {json.dumps(variables, indent=2)}")

            result = self.execute_mutation(mutation, variables)
            
            if result.get('errors'):
                logger.error(f"GraphQL error: {result['errors']}")
                return False

            user_errors = result.get('data', {}).get('productUpdate', {}).get('userErrors', [])
            if user_errors:
                for error in user_errors:
                    logger.error(f"User error: {error.get('message')} (Field: {error.get('field')})")
                return False

            updated_product = result.get('data', {}).get('productUpdate', {}).get('product', {})
            if updated_product:
                logger.info(f"Successfully updated product {updated_product.get('title')}")
                logger.info(f"New product type: {updated_product.get('productType')}")
                logger.info(f"New taxonomy: {updated_product.get('productCategory', {}).get('productTaxonomyNode', {})}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error in test update: {str(e)}")
            return False

    def print_taxonomy_hierarchy(self) -> None:
        """Print the full taxonomy hierarchy for debugging"""
        taxonomy = self.get_shopify_taxonomy()
        
        def print_node(node, level=0):
            indent = "  " * level
            node_id = node.get('id', '').split('/')[-1] if node.get('id') != 'root' else 'root'
            name = node.get('fullName', '') or node.get('name', '')
            print(f"{indent}- {name} (ID: {node_id})")
            
            children = node.get('children', {}).get('nodes', [])
            for child in children:
                print_node(child, level + 1)
        
        if taxonomy:
            print("\nAvailable Product Categories:")
            print_node(taxonomy)
        else:
            print("No product categories available")

    def get_taxonomy_mapping(self) -> Dict[str, str]:
        """Get mapping between standard taxonomy IDs and numeric IDs"""
        return {
            "aa-1-4": "160",  # Dresses
            "aa-1": "166",    # Clothing
            "aa": "165",      # Apparel & Accessories
        }
