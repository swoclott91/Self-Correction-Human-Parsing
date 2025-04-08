import requests
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import argparse

logger = logging.getLogger(__name__)

class TaxonomyFetcher:
    """Fetches and parses Shopify taxonomy data from GitHub"""
    
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Shopify/product-taxonomy/main/dist/en"
    TAXONOMY_FILES = {
        "categories": "/categories.json",
        "attributes": "/attributes.json",
        "values": "/attribute_values.json"
    }
    
    def __init__(self, output_dir: Optional[Path] = None, dry_run: bool = False):
        self.output_dir = output_dir or Path(__file__).parent
        self.dry_run = dry_run
        self.attributes = {}  # Initialize attributes dict
        if not dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def fetch_file(self, file_type: str) -> Optional[Dict]:
        """Fetch a taxonomy file from GitHub"""
        if file_type not in self.TAXONOMY_FILES:
            raise ValueError(f"Unknown file type: {file_type}")
            
        url = f"{self.GITHUB_RAW_BASE}{self.TAXONOMY_FILES[file_type]}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {file_type}: {e}")
            return None

    def process_categories(self, data: Dict) -> Dict:
        """Process raw category data into a more usable format"""
        processed = {}
        
        def process_category(cat: Dict) -> None:
            cat_id = cat['id']
            processed[cat_id] = {
                'name': cat['name'],
                'path': cat.get('full_name', cat['name']),
                'level': cat.get('level', 0),
                'children': [c['id'] for c in cat.get('children', [])],
                'allowed_attributes': [
                    attr['id'] 
                    for attr in cat.get('attributes', [])
                ],  # Extract attribute IDs from the attributes list
                'attribute_info': {  # Store full attribute info for reference
                    attr['id']: {
                        'name': attr['name'],
                        'handle': attr['handle'],
                        'description': attr.get('description'),
                        'extended': attr.get('extended', False)
                    }
                    for attr in cat.get('attributes', [])
                },
                'description': cat.get('description'),
                'meta': cat.get('meta', {}),
                'vertical': cat.get('vertical_name'),
                'parent_id': cat.get('parent_id'),  # Store parent relationship
                'ancestors': [  # Store ancestry information
                    {
                        'id': anc['id'],
                        'name': anc['name']
                    }
                    for anc in cat.get('ancestors', [])
                ]
            }
            
            # Process children recursively
            for child in cat.get('children', []):
                process_category(child)
        
        # Process categories from each vertical
        for vertical in data.get('verticals', []):
            vertical_name = vertical.get('name')
            logger.info(f"Processing vertical: {vertical_name}")
            
            for category in vertical.get('categories', []):
                # Add vertical context
                category['vertical_name'] = vertical_name
                process_category(category)
            
        return processed

    def process_attributes(self, data: Dict) -> Dict:
        """Process raw attribute data into a more usable format"""
        processed = {}
        
        for attr in data.get('attributes', []):
            attr_id = attr['id']
            attr_handle = attr['handle']
            
            processed[attr_id] = {
                'name': attr['name'],
                'handle': attr_handle,
                'type': attr.get('type', 'single_line_text_field'),
                'description': attr.get('description'),
                'required': attr.get('required', False),
                'validation': attr.get('validation', {}),
                'unit': attr.get('unit'),
                'meta': attr.get('meta', {}),
                'values': [  # Store the full value information
                    {
                        'id': v['id'],
                        'name': v['name'],
                        'handle': v['handle']
                    } for v in attr.get('values', [])
                ]
            }
            
            logger.debug(f"Attribute {attr['name']} has {len(attr.get('values', []))} values")
                
        return processed

    def process_values(self, data: Dict) -> Dict:
        """Process raw value data into a more usable format"""
        processed = {}
        
        # Process each value
        for value in data.get('values', []):
            value_id = value['id']
            
            # Get the attribute ID this value belongs to
            attr_id = None
            handle = value.get('handle', '')
            
            # Extract attribute handle from value handle (e.g. "top-length-type__long" -> "top-length-type")
            if '__' in handle:
                attr_handle = handle.split('__')[0]
                # Look up attribute ID by handle
                for aid, ainfo in self.attributes.items():
                    if ainfo.get('handle') == attr_handle:
                        attr_id = aid
                        break
            
            processed[value_id] = {
                'name': value['name'],
                'handle': handle,
                'attribute_id': attr_id,  # Store the parent attribute ID
                'description': value.get('description'),
                'meta': value.get('meta', {}),
                'translations': value.get('translations', {})
            }
            
            logger.debug(f"Processed value '{value['name']}' for attribute {attr_id} (from handle {handle})")
        
        # Log summary
        logger.info(f"Processed {len(processed)} values")
        
        return processed

    def fetch_and_save_all(self) -> bool:
        """Fetch and save all taxonomy files"""
        success = True
        
        # Process in specific order: attributes first, then categories and values
        file_order = ['attributes', 'categories', 'values']
        
        for file_type in file_order:
            logger.info(f"Fetching {file_type}...")
            
            raw_data = self.fetch_file(file_type)
            if not raw_data:
                success = False
                continue
            
            # Process the data
            processor = {
                'attributes': self.process_attributes,
                'categories': self.process_categories,
                'values': self.process_values
            }[file_type]
            
            processed_data = processor(raw_data)
            
            # Store attributes for later use
            if file_type == 'attributes':
                self.attributes = processed_data
            
            if not self.dry_run:
                output_file = self.output_dir / f"{file_type}.json"
                try:
                    with output_file.open('w') as f:
                        json.dump({
                            'version': raw_data.get('version'),
                            'updated_at': raw_data.get('updated_at'),
                            'data': processed_data
                        }, f, indent=2)
                    
                    size_mb = output_file.stat().st_size / (1024 * 1024)
                    logger.info(f"Saved {file_type} ({size_mb:.1f}MB) with {len(processed_data)} entries")
                    
                    # Log some sample data
                    if file_type == 'values':
                        sample_values = list(processed_data.items())[:3]
                        logger.debug("Sample processed values:")
                        for vid, vdata in sample_values:
                            logger.debug(f"  {vid}: {vdata['name']} (attribute: {vdata['attribute_id']})")
                except IOError as e:
                    logger.error(f"Failed to save {file_type}: {e}")
                    success = False
        
        return success

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Fetch and process Shopify taxonomy data')
    parser.add_argument('--dry-run', action='store_true', help='Process but don\'t save files')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    fetcher = TaxonomyFetcher(dry_run=args.dry_run)
    if fetcher.fetch_and_save_all():
        logger.info("Successfully fetched and saved all taxonomy data")
    else:
        logger.error("Failed to fetch some taxonomy data")

if __name__ == "__main__":
    main() 