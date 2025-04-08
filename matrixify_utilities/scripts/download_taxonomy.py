import requests
import json
from pathlib import Path
import logging
from typing import Dict, List, Optional
import time
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

class TaxonomyDownloader:
    """Downloads and processes Shopify's product taxonomy"""
    
    def __init__(self):
        # Update to 2024-04 API version
        self.admin_api_url = "https://color-couturier.myshopify.com/admin/api/2024-04/graphql.json"
        self.access_token = "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"
        
        if not self.admin_api_url or not self.access_token:
            logger.warning("Shopify API credentials not found in environment variables")
            
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize cache for processed data
        self.taxonomy_cache: Dict = {}
        self.id_mapping_cache: Dict = {}
        
    def download_taxonomy(self) -> Dict:
        """Download the complete Shopify taxonomy using GraphQL API"""
        logger.info("Downloading Shopify taxonomy...")
        
        def fetch_category(category_id: str) -> Dict:
            """Helper function to fetch a single category"""
            query = f"""
            {{
              taxonomy {{
                category(id: "{category_id}") {{
                  id
                  name
                  fullName
                  isRoot
                  isLeaf
                  parentId
                  ancestorIds
                  childrenIds
                }}
              }}
            }}
            """
            
            response = requests.post(
                self.admin_api_url,
                json={'query': query},
                headers={
                    'Content-Type': 'application/json',
                    'X-Shopify-Access-Token': self.access_token
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and data['data']['taxonomy']['category']:
                return data['data']['taxonomy']['category']
            return None
        
        def process_category_tree(category_id: str, all_categories: Dict, depth: int = 0):
            """Recursively process category and its children"""
            if depth > 10:  # Safety limit for recursion depth
                return
                
            # Don't refetch if we already have this category
            if category_id in all_categories:
                return
                
            # Fetch category details
            category = fetch_category(category_id)
            if not category:
                return
                
            # Store category
            all_categories[category_id] = category
            logger.info(f"{'  ' * depth}Fetched: {category['name']}")
            
            # Process children
            for child_id in category.get('childrenIds', []):
                time.sleep(0.5)  # Add delay between requests
                process_category_tree(child_id, all_categories, depth + 1)
        
        try:
            # First get root categories
            root_query = """
            {
              taxonomy {
                categories(first: 250) {
                  edges {
                    node {
                      id
                      name
                      fullName
                      isRoot
                      isLeaf
                      parentId
                      ancestorIds
                      childrenIds
                    }
                  }
                }
              }
            }
            """
            
            response = requests.post(
                self.admin_api_url,
                json={'query': root_query},
                headers={
                    'Content-Type': 'application/json',
                    'X-Shopify-Access-Token': self.access_token
                }
            )
            response.raise_for_status()
            root_data = response.json()
            
            # Process all categories
            all_categories = {}
            root_categories = (root_data.get('data', {})
                             .get('taxonomy', {})
                             .get('categories', {})
                             .get('edges', []))
            
            # First store all root categories
            for edge in root_categories:
                node = edge['node']
                all_categories[node['id']] = node
            
            # Then process each root category's children
            for edge in root_categories:
                node = edge['node']
                logger.info(f"\nProcessing category tree: {node['name']}")
                for child_id in node.get('childrenIds', []):
                    time.sleep(0.5)  # Add delay between requests
                    process_category_tree(child_id, all_categories)
            
            # Create final data structure
            taxonomy_data = {
                'data': {
                    'taxonomy': {
                        'categories': {
                            'edges': [
                                {'node': category} 
                                for category in all_categories.values()
                            ]
                        }
                    }
                }
            }
            
            # Save raw taxonomy
            self._save_json(taxonomy_data, 'raw_taxonomy.json')
            logger.info(f"\nSuccessfully downloaded taxonomy data with {len(all_categories)} categories")
            
            return taxonomy_data
            
        except requests.RequestException as e:
            logger.error(f"Failed to download taxonomy: {e}")
            # Try to load from cache
            logger.info("Attempting to load from cached taxonomy file...")
            cached_data = self._load_json('raw_taxonomy.json')
            if cached_data:
                logger.info("Successfully loaded from cache")
                return cached_data
            raise
            
    def process_taxonomy(self, taxonomy_data: Optional[Dict] = None) -> Dict:
        """Process taxonomy data into useful formats"""
        if taxonomy_data is None:
            taxonomy_data = self._load_json('raw_taxonomy.json')
            
        if not taxonomy_data:
            raise ValueError("No taxonomy data available to process")
            
        logger.info("Processing taxonomy data...")
        
        processed_data = {
            'categories': {},  # Path to ID mapping
            'ids': {},        # ID to path mapping
            'gids': {},       # GID to path mapping
            'hierarchy': {},  # Full category hierarchy
            'metadata': {     # Additional taxonomy metadata
                'last_updated': time.time(),
                'version': taxonomy_data.get('version', 'unknown')
            }
        }
        
        # First, build a lookup of all categories by ID
        categories_by_id = {}
        for edge in taxonomy_data.get('data', {}).get('taxonomy', {}).get('categories', {}).get('edges', []):
            node = edge['node']
            categories_by_id[node['id']] = node
        
        def build_path(category_id: str) -> str:
            """Build the full path for a category using its ancestors"""
            category = categories_by_id.get(category_id)
            if not category:
                return ''
                
            path_parts = []
            current_id = category_id
            
            while current_id:
                current = categories_by_id.get(current_id)
                if current:
                    path_parts.insert(0, current['name'])
                    current_id = current.get('parentId')
                else:
                    break
                    
            return ' > '.join(path_parts)
        
        # Process all categories
        total_categories = 0
        for category_id, category in categories_by_id.items():
            path = build_path(category_id)
            if path:
                processed_data['categories'][path] = {
                    'id': category['id'],
                    'gid': category['id'],
                    'name': category['name'],
                    'fullName': category.get('fullName', ''),
                    'isRoot': category.get('isRoot', False),
                    'isLeaf': category.get('isLeaf', False),
                    'parentId': category.get('parentId'),
                    'childrenIds': category.get('childrenIds', [])
                }
                processed_data['ids'][category['id']] = path
                processed_data['gids'][category['id']] = path
                
                # Build hierarchy
                parent_path = ' > '.join(path.split(' > ')[:-1])
                if parent_path not in processed_data['hierarchy']:
                    processed_data['hierarchy'][parent_path] = []
                if path not in processed_data['hierarchy']:
                    processed_data['hierarchy'][path] = []
                if parent_path:  # Don't add root categories to hierarchy
                    processed_data['hierarchy'][parent_path].append(path)
                    
                total_categories += 1
        
        # Save processed data
        self._save_json(processed_data, 'processed_taxonomy.json')
        logger.info(f"Successfully processed {total_categories} categories")
        logger.info(f"Sample paths:")
        # Print a few sample paths to verify
        for i, path in enumerate(list(processed_data['categories'].keys())[:5]):
            logger.info(f"  {i+1}. {path}")
        
        return processed_data
        
    def get_category_id(self, category_path: str) -> Optional[str]:
        """Get numeric ID for category path"""
        if not self.taxonomy_cache:
            self.taxonomy_cache = self._load_json('processed_taxonomy.json')
            
        category_data = self.taxonomy_cache.get('categories', {}).get(category_path)
        return category_data['id'] if category_data else None
        
    def get_category_gid(self, category_path: str) -> Optional[str]:
        """Get Shopify GID for category path"""
        if not self.taxonomy_cache:
            self.taxonomy_cache = self._load_json('processed_taxonomy.json')
            
        category_data = self.taxonomy_cache.get('categories', {}).get(category_path)
        return category_data['gid'] if category_data else None
        
    def get_category_path(self, identifier: str) -> Optional[str]:
        """Get category path from ID or GID"""
        if not self.taxonomy_cache:
            self.taxonomy_cache = self._load_json('processed_taxonomy.json')
            
        # Check if it's a GID
        if identifier.startswith('gid://'):
            return self.taxonomy_cache.get('gids', {}).get(identifier)
            
        # Otherwise treat as numeric ID
        return self.taxonomy_cache.get('ids', {}).get(identifier)
        
    def _save_json(self, data: Dict, filename: str) -> None:
        """Save data to JSON file"""
        file_path = self.data_dir / filename
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
            
    def _load_json(self, filename: str) -> Dict:
        """Load data from JSON file"""
        file_path = self.data_dir / filename
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

def main():
    """Main execution function"""
    downloader = TaxonomyDownloader()
    
    try:
        # Download fresh taxonomy data
        taxonomy_data = downloader.download_taxonomy()
        
        # Process the taxonomy
        processed_data = downloader.process_taxonomy(taxonomy_data)
        
        # Basic validation
        if not processed_data['categories']:
            raise ValueError("No categories found in processed taxonomy")
            
        logger.info(f"Successfully processed {len(processed_data['categories'])} categories")
        
    except Exception as e:
        logger.error(f"Failed to update taxonomy: {e}")
        raise

if __name__ == '__main__':
    main() 