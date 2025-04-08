import unittest
import logging
import sys
from pathlib import Path
import json

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))

from taxonomy_mapper import TaxonomyMapper

logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG to see more info
logger = logging.getLogger(__name__)

class TestTaxonomyMapper(unittest.TestCase):
    """Test cases for TaxonomyMapper"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        # Set logging to DEBUG for more information
        logging.getLogger('taxonomy_mapper').setLevel(logging.DEBUG)
        
        cls.mapper = TaxonomyMapper()
        cls.mapper.build_category_maps()
        
        # Get actual categories to test with
        all_paths = list(cls.mapper.path_to_id.keys())
        if not all_paths:
            raise ValueError("No categories loaded from taxonomy")
            
        # Select test paths that we know exist
        cls.test_cases = [
            {
                'path': "Vehicles & Parts",
                'id': "gid://shopify/TaxonomyCategory/vp",
                'has_children': True
            },
            {
                'path': "Vehicles & Parts > Vehicles",
                'id': "gid://shopify/TaxonomyCategory/vp-2",
                'has_children': True
            },
            {
                'path': "Apparel & Accessories",
                'id': "gid://shopify/TaxonomyCategory/aa",
                'has_children': True
            }
        ]
        
        logger.info("\nTest cases:")
        for case in cls.test_cases:
            logger.info(f"Path: {case['path']}")
            logger.info(f"ID: {case['id']}")
            logger.info(f"Has children: {case['has_children']}\n")
    
    def test_taxonomy_download(self):
        """Test downloading taxonomy data"""
        taxonomy_data = self.mapper.update_taxonomy(force=True)
        self.assertIsNotNone(taxonomy_data)
        self.assertTrue(len(taxonomy_data) > 0)
        
        # Check cache file exists and has content
        cache_file = self.mapper.data_dir / 'categories.json'
        self.assertTrue(cache_file.exists())
        self.assertTrue(cache_file.stat().st_size > 0)
    
    def test_path_to_id_mapping(self):
        """Test converting category paths to IDs"""
        for test_case in self.test_cases:
            category_id = self.mapper.get_category_id(test_case['path'])
            self.assertEqual(
                category_id, 
                test_case['id'],
                f"Path '{test_case['path']}' should map to ID '{test_case['id']}'"
            )
    
    def test_id_to_path_mapping(self):
        """Test converting category IDs to paths"""
        for test_case in self.test_cases:
            path = self.mapper.get_category_path(test_case['id'])
            self.assertEqual(
                path, 
                test_case['path'],
                f"ID '{test_case['id']}' should map to path '{test_case['path']}'"
            )
    
    def test_subcategories(self):
        """Test listing subcategories"""
        for test_case in self.test_cases:
            subcats = self.mapper.list_categories(test_case['path'])
            if test_case['has_children']:
                self.assertTrue(
                    len(subcats) > 0,
                    f"Category '{test_case['path']}' should have subcategories"
                )
    
    def test_invalid_inputs(self):
        """Test handling of invalid inputs"""
        self.assertIsNone(
            self.mapper.get_category_id("Not A Real Category"),
            "Invalid path should return None"
        )
        self.assertIsNone(
            self.mapper.get_category_path("not-a-real-id"),
            "Invalid ID should return None"
        )
        
    def test_metadata(self):
        """Test that we're storing category metadata"""
        for test_case in self.test_cases:
            metadata = self.mapper.taxonomy_cache.get(test_case['id'])
            self.assertIsNotNone(metadata, "Should have metadata for category")
            self.assertIn('name', metadata, "Metadata should include name")
            self.assertIn('level', metadata, "Metadata should include level")
    
    def test_whitespace_handling(self):
        """Test handling of whitespace in IDs and paths"""
        # Test with extra spaces
        path = "  Vehicles & Parts  "
        category_id = "  gid://shopify/TaxonomyCategory/vp  "
        
        # Should handle extra whitespace in paths
        self.assertEqual(
            self.mapper.get_category_id(path),
            "gid://shopify/TaxonomyCategory/vp",
            "Should handle whitespace in paths"
        )
        
        # Should handle extra whitespace in IDs
        self.assertEqual(
            self.mapper.get_category_path(category_id),
            "Vehicles & Parts",
            "Should handle whitespace in IDs"
        )

def main():
    unittest.main(verbosity=2)

if __name__ == "__main__":
    main() 