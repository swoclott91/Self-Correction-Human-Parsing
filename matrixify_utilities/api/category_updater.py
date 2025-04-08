from typing import Dict, Optional, List
import logging
from .client import ShopifyClient
from .graphql_mutations import PRODUCT_UPDATE_MUTATION, GET_PRODUCT_QUERY

logger = logging.getLogger(__name__)

class CategoryUpdater:
    """Handles Shopify API interactions for updating product categories and metafields"""
    
    def __init__(self, client: Optional[ShopifyClient] = None):
        self.client = client or ShopifyClient()

    def _format_gid(self, id_str: str, type_prefix: str = "Product") -> str:
        """Format ID as Shopify Global ID if needed"""
        if id_str.startswith('gid://'):
            return id_str
        return f"gid://shopify/{type_prefix}/{id_str.strip()}"

    def get_product(self, product_id: str) -> Optional[Dict]:
        """Fetch product details including category and metafields"""
        try:
            result = self.client.graphql_query(
                GET_PRODUCT_QUERY, 
                {"id": self._format_gid(product_id)}
            )
            
            if 'errors' in result:
                logger.error(f"GraphQL errors: {result['errors']}")
                return None
            
            product = result.get('data', {}).get('product')
            if not product:
                logger.error(f"No product data returned for ID: {product_id}")
                return None
            
            logger.info(f"Successfully fetched product: {product.get('title')}")
            return product

        except Exception as e:
            logger.error(f"Failed to fetch product {product_id}: {e}")
            return None

    def update_product(self, product_id: str, updates: Dict) -> Dict:
        """
        Update product with category and/or metafields
        
        Args:
            product_id: Product ID or GID
            updates: Dict containing update data:
                {
                    "category": "gid://shopify/...",  # Optional
                    "metafields": [{                  # Optional
                        "namespace": str,
                        "key": str,
                        "value": str,
                        "type": str
                    }],
                    "properties": [{                  # Optional
                        "key": str,
                        "value": str or [str]
                    }]
                }
        """
        variables = {
            "input": {
                "id": self._format_gid(product_id),
                **{k: v for k, v in updates.items() if v}
            }
        }

        result = self.client.graphql_query(PRODUCT_UPDATE_MUTATION, variables)
        
        # Handle errors
        if 'errors' in result:
            logger.error(f"GraphQL errors: {result['errors']}")
            return result
            
        user_errors = result.get('data', {}).get('productUpdate', {}).get('userErrors', [])
        if user_errors:
            logger.error(f"User errors: {user_errors}")
            return result

        # Log success
        updated_product = result.get('data', {}).get('productUpdate', {}).get('product', {})
        if updated_product:
            logger.info(f"Successfully updated product: {updated_product.get('title', product_id)}")
            
            if 'category' in updates and updated_product.get('category'):
                logger.info(f"Updated category: {updated_product['category'].get('name')}")
                
            if 'metafields' in updates:
                logger.info("Updated metafields:")
                for mf in updated_product.get('metafields', {}).get('nodes', []):
                    logger.info(f"  {mf['namespace']}.{mf['key']}: {mf['value']}")
                    
            if 'properties' in updates:
                logger.info("Updated properties:")
                for prop in updated_product.get('properties', []):
                    logger.info(f"  {prop['key']}: {prop['value']}")

        return result

    def get_products(self, filters: Dict[str, any]) -> List[Dict]:
        """
        Get products matching filters
        
        Args:
            filters: Dict of filter options:
                - created_at_min: ISO timestamp
                - status: str
                - ids: List[str]
                - limit: int (default 250)
        """
        # Build query string
        query_parts = []
        if filters.get('created_at_min'):
            query_parts.append(f"created_at:>'{filters['created_at_min']}'")
        if filters.get('status'):
            query_parts.append(f"status:{filters['status']}")
        if filters.get('ids'):
            id_list = ','.join(filters['ids'])
            query_parts.append(f"id:({id_list})")
            
        query_str = ' AND '.join(query_parts)
        
        # Get all products (handles pagination)
        all_products = []
        has_next = True
        cursor = None
        
        while has_next:
            variables = {
                'first': min(filters.get('limit', 250), 250),  # Enforce API limit
                'after': cursor,
                'query': query_str
            }
            
            result = self.client.graphql_query(GET_PRODUCTS_QUERY, variables)
            
            if 'errors' in result:
                logger.error(f"GraphQL errors: {result['errors']}")
                break
                
            products = result.get('data', {}).get('products')
            if not products:
                break
                
            all_products.extend(products['nodes'])
            
            # Check pagination
            page_info = products['pageInfo']
            has_next = page_info['hasNextPage']
            cursor = page_info['endCursor']
                
        return all_products 