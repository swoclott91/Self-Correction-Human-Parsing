import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime

from .client import ShopifyClient
from .metaobject_registry import MetaobjectRegistry

logger = logging.getLogger(__name__)

class ColorMetaobjectCreator:
    def __init__(self, client: ShopifyClient, registry: Optional[MetaobjectRegistry] = None):
        self.client = client
        self.registry = registry or MetaobjectRegistry()
        
        # Ensure we have the definition ID
        self._ensure_definition_id()
        
    def _ensure_definition_id(self):
        """Get and cache the color_pattern definition ID"""
        definition_id = self.registry.get_definition_id('color')
        if not definition_id:
            # Fetch from Shopify
            definitions = self.client.get_metaobject_definitions()
            for definition in definitions:
                # Check both formats of the type name
                if definition['type'] in ['color_pattern', 'shopify--color-pattern']:
                    self.registry.set_definition_id('color', definition['id'])
                    logger.info(f"Found color pattern definition: {definition['id']}")
                    return
            raise ValueError("Could not find color pattern definition ID")
            
    def create_color_metaobjects(self, color_data_list: List[Dict], 
                                batch_size: int = 50, 
                                dry_run: bool = False) -> Tuple[List[str], List[str]]:
        """Create multiple color metaobjects
        
        Returns:
            Tuple of (created_handles, failed_handles)
        """
        created_handles = []
        failed_handles = []
        
        # Group into batches
        for i in range(0, len(color_data_list), batch_size):
            batch = color_data_list[i:i + batch_size]
            
            # Process batch
            batch_metaobjects = []
            for color_data in batch:
                handle = f"color-{color_data['handle']}"
                
                # Skip if in cache or exists
                if self.registry.get_color(handle):
                    logger.info(f"Using cached metaobject: {handle}")
                    created_handles.append(handle)
                    continue
                    
                if self.client.validate_metaobject('color_pattern', handle):
                    logger.info(f"Metaobject already exists: {handle}")
                    self.registry.register_color(handle, color_data)
                    created_handles.append(handle)
                    continue
                
                # Add to batch
                batch_metaobjects.append({
                    "handle": handle,
                    "fields": [
                        {"key": "label", "value": color_data['name']},
                        {"key": "color", "value": color_data['hex']},
                        {"key": "color_taxonomy_reference", "value": color_data['color_taxonomy']},
                        {"key": "pattern_taxonomy_reference", "value": color_data['pattern_taxonomy']}
                    ]
                })
            
            if not batch_metaobjects:
                continue
                
            if dry_run:
                logger.info(f"Would create {len(batch_metaobjects)} metaobjects")
                created_handles.extend([m['handle'] for m in batch_metaobjects])
                continue
                
            try:
                # Create batch
                definition_id = self.registry.get_definition_id('color')
                new_handles = self.client.create_metaobjects_batch(
                    definition_id,
                    batch_metaobjects
                )
                
                # Update registry
                for handle, color_data in zip([m['handle'] for m in batch_metaobjects], batch):
                    if handle in new_handles:
                        self.registry.register_color(handle, color_data)
                        created_handles.append(handle)
                    else:
                        failed_handles.append(handle)
                        
            except Exception as e:
                logger.error(f"Error creating batch: {e}")
                failed_handles.extend([m['handle'] for m in batch_metaobjects])
                
        return created_handles, failed_handles 