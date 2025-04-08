from typing import Dict, Optional, List
import logging
import json
from .client import ShopifyClient

logger = logging.getLogger(__name__)

class MetafieldUpdater:
    """Handles product metafield updates via Shopify API"""
    
    METAFIELD_MAPPINGS = {
        'fabric': {
            'namespace': 'shopify',
            'key': 'fabric',
            'type': 'list.metaobject_reference',
            'metaobject_type': 'shopify--fabric'
        },
        'neckline': {
            'namespace': 'shopify',
            'key': 'neckline',
            'type': 'list.metaobject_reference',
            'metaobject_type': 'shopify--neckline'
        },
        'sleeve_length_type': {
            'namespace': 'shopify',
            'key': 'sleeve-length-type',
            'type': 'list.metaobject_reference',
            'metaobject_type': 'shopify--sleeve-length-type'
        },
        'clothing_features': {
            'namespace': 'shopify',
            'key': 'clothing-features',
            'type': 'list.metaobject_reference',
            'metaobject_type': 'shopify--clothing-features'
        },
        'color_pattern': {
            'namespace': 'shopify',
            'key': 'color-pattern',
            'type': 'list.metaobject_reference',
            'metaobject_type': 'shopify--color-pattern'
        },
        'size': {
            'namespace': 'shopify',
            'key': 'size',
            'type': 'list.metaobject_reference',
            'metaobject_type': 'shopify--size'
        },
        'care_instructions': {
            'namespace': 'shopify',
            'key': 'care-instructions',
            'type': 'list.metaobject_reference',
            'metaobject_type': 'shopify--care-instructions'
        },
        'age_group': {
            'namespace': 'shopify',
            'key': 'age-group',
            'type': 'list.metaobject_reference',
            'metaobject_type': 'shopify--age-group'
        },
        'target_gender': {
            'namespace': 'shopify',
            'key': 'target-gender',
            'type': 'list.metaobject_reference',
            'metaobject_type': 'shopify--target-gender'
        }
    }
    
    def __init__(self, client: Optional[ShopifyClient] = None):
        """Initialize with optional client, or create new one"""
        self.client = client or ShopifyClient()
        self._metafield_definitions = None  # Cache definitions
        self._metaobject_definitions = None
        
    def get_metafield_definitions(self, force_refresh=False) -> List[Dict]:
        """Get or cache metafield definitions"""
        if self._metafield_definitions is None or force_refresh:
            query = """
            query getMetafieldDefinitions {
                metafieldDefinitions(ownerType: PRODUCT, first: 50) {
                    nodes {
                        id
                        name
                        key
                        namespace
                        type {
                            name
                        }
                        validations {
                            name
                            value
                        }
                    }
                }
            }
            """
            result = self.client.graphql_query(query)
            self._metafield_definitions = result.get('data', {}).get('metafieldDefinitions', {}).get('nodes', [])
            
        return self._metafield_definitions
    
    def validate_metafield_value(self, key: str, value: str) -> bool:
        """Validate a metafield value against available options"""
        if not value:
            return False
            
        # Get available metaobjects if not cached
        if not self._metaobject_definitions:
            self._metaobject_definitions = self.get_metaobject_definitions()
            
        # Get mapping for this key
        mapping = self.METAFIELD_MAPPINGS.get(key)
        if not mapping:
            logger.warning(f"No mapping found for metafield {key}")
            return False
            
        # Check if metaobject type exists
        metaobject_type = mapping['metaobject_type']
        if metaobject_type not in self._metaobject_definitions:
            logger.warning(f"No definition found for {metaobject_type}")
            return False
            
        # For each value, check if it exists
        values = [v.strip() for v in value.split(',')]
        for val in values:
            if '.' in val:
                obj_type, obj_handle = val.split('.')
                if obj_type != metaobject_type:
                    logger.warning(f"Invalid metaobject type: {obj_type} for {key}")
                    return False
                if obj_handle not in self._metaobject_definitions[obj_type]['values']:
                    logger.warning(f"Invalid value {obj_handle} for {obj_type}")
                    return False
            else:
                logger.warning(f"Invalid format for metaobject reference: {val}")
                return False
                
        return True
    
    def format_metafield_value(self, key: str, value: str) -> Optional[str]:
        """Format and validate metafield value"""
        if not self.validate_metafield_value(key, value):
            return None
            
        # Split multiple values
        values = [v.strip() for v in value.split(',')]
        
        # Get metaobject IDs
        mapping = self.METAFIELD_MAPPINGS[key]
        metaobject_type = mapping['metaobject_type']
        
        mapped_values = []
        for val in values:
            obj_type, obj_handle = val.split('.')
            obj_id = self._metaobject_definitions[obj_type]['values'][obj_handle]
            mapped_values.append(obj_id)
            
        # Always return as JSON array even for single values
        return json.dumps(mapped_values)
    
    def update_product_metafields(self, product_id: str, metafields: Dict[str, str]) -> Dict:
        """Update product metafields"""
        
        # First get available metafield definitions
        metafield_defs = self.get_metafield_definitions()
        logger.info(f"Found {len(metafield_defs)} metafield definitions")
        
        # Get metaobject definitions and values
        metaobject_defs = self.get_metaobject_definitions()
        
        # Format metafields for update
        formatted_metafields = []
        for key, value in metafields.items():
            if not value:
                continue
                
            # Find matching definition
            definition = next(
                (d for d in metafield_defs 
                 if d['key'] == key.replace('_', '-') and d['namespace'] == 'shopify'),
                None
            )
            
            if definition:
                # Handle multiple values
                values = [v.strip() for v in value.split(',')]
                
                metaobject_type = f"shopify--{key.replace('_', '-')}"
                
                if metaobject_type in metaobject_defs:
                    metaobject_ids = []
                    for val in values:
                        # Remove the type prefix if it exists (e.g., "shopify--fabric.cotton" -> "cotton")
                        val_handle = val.split('.')[-1] if '.' in val else val
                        if val_handle in metaobject_defs[metaobject_type]['values']:
                            metaobject_id = metaobject_defs[metaobject_type]['values'][val_handle]
                            metaobject_ids.append(metaobject_id)
                            logger.info(f"Adding metafield {key}: {val_handle}")
                    
                    if metaobject_ids:
                        formatted_metafields.append({
                            "namespace": "shopify",
                            "key": key.replace('_', '-'),
                            "value": json.dumps(metaobject_ids),
                            "type": "list.metaobject_reference"
                        })
                else:
                    logger.warning(f"No metaobject definition found for {metaobject_type}")
            else:
                logger.warning(f"No metafield definition found for {key}")
        
        # Update mutation
        mutation = """
        mutation productUpdate($input: ProductInput!) {
            productUpdate(input: $input) {
                product {
                    id
                    metafields(first: 50) {
                        nodes {
                            id
                            namespace
                            key
                            value
                            type
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

        # Clean product ID - remove prefix if already exists
        clean_id = product_id.replace('gid://shopify/Product/', '')
        product_gid = f"gid://shopify/Product/{clean_id}"

        variables = {
            "input": {
                "id": product_gid,
                "metafields": formatted_metafields
            }
        }

        result = self.client.graphql_query(mutation, variables)
        
        # Handle errors
        if 'errors' in result:
            logger.error(f"GraphQL errors: {result['errors']}")
            return None
        
        user_errors = result.get('data', {}).get('productUpdate', {}).get('userErrors', [])
        if user_errors:
            logger.error(f"User errors: {user_errors}")
            return None

        # Log success
        updated_product = result.get('data', {}).get('productUpdate', {}).get('product', {})
        if updated_product:
            logger.info("Successfully updated metafields:")
            for mf in updated_product.get('metafields', {}).get('nodes', []):
                logger.info(f"  {mf['namespace']}.{mf['key']}: {mf['value']}")

        return result
    
    def get_metaobject_definitions(self) -> Dict[str, Dict]:
        """Get available metaobject definitions and their values"""
        query = """
        query getMetaobjectDefinitions {
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
                    metaobjects(first: 100) {
                        nodes {
                            id
                            handle
                            fields {
                                key
                                value
                                reference {
                                    ... on Metaobject {
                                        id
                                        handle
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        result = self.client.graphql_query(query)
        definitions = result.get('data', {}).get('metaobjectDefinitions', {}).get('nodes', [])
        
        # Map definitions by type
        mapped_definitions = {}
        for definition in definitions:
            def_type = definition['type']  # e.g. 'shopify--fabric'
            values = {
                metaobj['handle']: metaobj['id']
                for metaobj in definition.get('metaobjects', {}).get('nodes', [])
            }
            logger.debug(f"Available values for {def_type}: {list(values.keys())}")
            
            mapped_definitions[def_type] = {
                'id': definition['id'],
                'name': definition['name'],
                'values': values
            }
            logger.info(f"Found {len(mapped_definitions[def_type]['values'])} values for {def_type}")
            
        return mapped_definitions 