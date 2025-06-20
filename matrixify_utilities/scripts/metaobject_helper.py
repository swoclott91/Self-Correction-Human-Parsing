"""
Metaobject Sync Helper

This script helps resolve and cache Shopify metaobject GIDs for attribute references.
"""

import os
import requests
import logging
from typing import Dict, Optional, List
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class MetaobjectResolver:
    """Resolves taxonomy values to metaobject GIDs"""
    
    ATTRIBUTE_TYPE_MAP = {
        'size': 'shopify--size',
        'fabric': 'shopify--fabric',
        'target-gender': 'shopify--target-gender',
        'waist-rise': 'shopify--waist-rise',
        'skirt-dress-length-type': 'shopify--skirt-dress-length-type',
        'age-group': 'shopify--age-group',
        'dress-occasion': 'shopify--dress-occasion',
        'color': 'shopify--color',
        'pattern': 'shopify--pattern',
        'clothing-features': 'shopify--clothing-features',
        'fit': 'shopify--fit',
        'skirt-style': 'shopify--skirt-style',
        'sleeve-length-type': 'shopify--sleeve-length-type',
        'neckline': 'shopify--neckline',
        'dress-style': 'shopify--dress-style',
        'pants-length-type': 'shopify--pants-length-type',
        'top-length-type': 'shopify--top-length-type',
        'outerwear-clothing-features': 'shopify--outerwear-clothing-features',
        'intimate-apparel-features': 'shopify--intimate-apparel-features'
    }
    
    def __init__(self, taxonomy_dir: Optional[Path] = None, shop_url: Optional[str] = None, access_token: Optional[str] = None):
        """Initialize with taxonomy directory and optional Shopify credentials"""
        self.taxonomy_dir = taxonomy_dir or Path(__file__).parent.parent / 'taxonomy_data'
        self.shop_url = shop_url
        self.access_token = access_token
        
        # Load attribute data
        attributes_file = self.taxonomy_dir / 'apparel_accessories_attributes.json'
        with open(attributes_file) as f:
            self.attributes_data = json.load(f)
        
        # Load values data
        values_file = self.taxonomy_dir / 'values.json'
        with open(values_file) as f:
            self.values_data = json.load(f)
        
        # Load GID cache
        cache_path = Path(__file__).parent.parent / 'metaobject_sync/gid_cache.json'
        logger.debug(f"Loading GID cache from: {cache_path}")
        try:
            with open(cache_path) as f:
                self.gid_cache = json.load(f)
                logger.debug(f"Loaded {len(self.gid_cache)} cache entries")
        except Exception as e:
            logger.error(f"Failed to load GID cache: {e}")
            self.gid_cache = {}

    def _build_lookup_maps(self):
        """Build attribute and value lookup maps"""
        # Map attributes
        for vertical in self.attributes_data.get("verticals", []):
            if vertical["name"] == "Apparel & Accessories":
                for category in vertical.get("categories", []):
                    for attr in category.get("attributes", []):
                        handle = attr.get("handle")
                        attr_id = attr.get("id")
                        if handle and attr_id:
                            self.attribute_map[handle] = attr_id
        
        # Map values
        for value_id, value in self.values_data.get("data", {}).items():
            attr_id = value.get("attribute_id")
            if attr_id:
                if attr_id not in self.value_map:
                    self.value_map[attr_id] = {}
                handle = value.get("handle", "").split("__")[-1]  # Get value part
                self.value_map[attr_id][handle] = value_id

    def warm_cache(self, metaobject_types: List[str]) -> None:
        """Pre-fetch and cache metaobjects for the given types"""
        for meta_type in metaobject_types:
            logger.info(f"Warming cache for metaobject type: {meta_type}")
            if meta_type in self.ATTRIBUTE_TYPE_MAP.values():
                # Cache is already loaded from file
                logger.debug(f"Cache already loaded for {meta_type}")
            else:
                logger.warning(f"Unknown metaobject type: {meta_type}")

    def get_metaobject_gid(self, taxonomy_value_id: str) -> Optional[str]:
        """Get metaobject GID for a taxonomy value"""
        try:
            # Handle both full GID and ID-only formats
            if not taxonomy_value_id.startswith('gid://'):
                full_gid = f"gid://shopify/TaxonomyValue/{taxonomy_value_id}"
            else:
                full_gid = taxonomy_value_id

            logger.debug(f"Looking up taxonomy value with GID: {full_gid}")

            # Get value info from taxonomy data
            value_info = self.values_data.get('data', {}).get(full_gid)
            if not value_info:
                logger.warning(f"No value found for taxonomy ID {taxonomy_value_id}")
                return None

            logger.debug(f"Found value info: {value_info}")

            # Get attribute handle and value name
            handle = value_info.get('handle', '')
            if not handle or '__' not in handle:
                logger.warning(f"Invalid handle format: {handle}")
                return None

            # Split handle into attribute and value parts
            attr_handle, value_handle = handle.split('__')
            logger.debug(f"Split handle into: attr={attr_handle}, value={value_handle}")

            # Look up in GID cache
            attr_cache = self.gid_cache.get(attr_handle)
            if not attr_cache:
                logger.warning(f"No cache entry found for attribute: {attr_handle}")
                logger.debug(f"Available attributes in cache: {list(self.gid_cache.keys())}")
                return None

            # Look up value in attribute cache
            metaobject_gid = attr_cache.get(value_handle)
            if metaobject_gid:
                logger.debug(f"✅ Found metaobject GID in cache: {metaobject_gid}")
                return metaobject_gid
            else:
                logger.warning(f"No cache entry found for value '{value_handle}' in {attr_handle}")
                logger.debug(f"Available values for {attr_handle}: {list(attr_cache.keys())}")
                return None

        except Exception as e:
            logger.error(f"Error resolving metaobject GID: {str(e)}")
            logger.error(f"Stack trace:", exc_info=True)
            return None

    def resolve_gid(self, taxonomy_value_id: str, attribute_handle: str) -> Optional[str]:
        """Resolve taxonomy value ID to metaobject GID"""
        logger.debug(f"resolve_gid called with: taxonomy_value_id={taxonomy_value_id}, attribute_handle={attribute_handle}")
        
        # Get metaobject type from mapping
        metaobject_type = self.ATTRIBUTE_TYPE_MAP.get(attribute_handle)
        logger.debug(f"Metaobject type from mapping: {metaobject_type}")
        if not metaobject_type:
            logger.warning(f"No metaobject type mapping for {attribute_handle}")
            return None

        # Get value info from taxonomy data
        full_gid = f"gid://shopify/TaxonomyValue/{taxonomy_value_id}"
        value_info = self.values_data.get('data', {}).get(full_gid)
        logger.debug(f"Value info from taxonomy data: {value_info}")
        if not value_info:
            logger.warning(f"No value found for taxonomy ID {taxonomy_value_id}")
            return None

        # Get handle from value info
        handle = value_info.get('handle', '')
        logger.debug(f"Handle from value info: {handle}")
        if not handle or '__' not in handle:
            logger.warning(f"Invalid handle format: {handle}")
            return None

        # Get value part of handle
        value_handle = handle.split('__')[-1]
        logger.debug(f"Value handle: {value_handle}")

        # Look up in GID cache
        attr_cache = self.gid_cache.get(attribute_handle)
        logger.debug(f"Attribute cache entries: {list(self.gid_cache.keys())}")
        if not attr_cache:
            logger.warning(f"No cache entry found for attribute: {attribute_handle}")
            return None

        # Get metaobject GID from cache
        metaobject_gid = attr_cache.get(value_handle)
        logger.debug(f"Found metaobject GID: {metaobject_gid}")
        if not metaobject_gid:
            logger.warning(f"No cache entry found for value {value_handle} in {attribute_handle}")
            return None

        return metaobject_gid

def main():
    logging.basicConfig(level=logging.INFO)
    metaobject_types = [
        "shopify--age-group",
        "shopify--fabric",
        "shopify--target-gender",
        "shopify--skirt-dress-length-type",
        "shopify--dress-occasion"
    ]

    all_metaobjects = {}
    for meta_type in metaobject_types:
        logging.info(f"Fetching metaobjects for type: {meta_type}")
        type_map = fetch_metaobjects_by_type(meta_type)
        all_metaobjects.update(type_map)

    for key, gid in all_metaobjects.items():
        print(f"{key}: {gid}")


if __name__ == "__main__":
    main()
