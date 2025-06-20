from typing import Dict, Optional, List, Tuple
import logging
from pathlib import Path
from dataclasses import dataclass
from .clothing_categorizer import ClothingCategorizer
from .taxonomy_mapper import TaxonomyMapper

logger = logging.getLogger(__name__)

@dataclass
class EnrichmentResult:
    """Container for product enrichment results"""
    product_id: str
    category_id: Optional[str] = None
    category_path: Optional[str] = None
    confidence: float = 0.0
    attributes: Dict[str, str] = None
    errors: List[str] = None
    
    def __post_init__(self):
        self.attributes = self.attributes or {}
        self.errors = self.errors or []
        
    @property
    def is_valid(self) -> bool:
        return bool(self.category_id and not self.errors)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format"""
        return {
            'product_id': self.product_id,
            'category_id': self.category_id,
            'category_path': self.category_path,
            'confidence': self.confidence,
            'attributes': self.attributes,
            'errors': self.errors,
            'is_valid': self.is_valid
        }

class ProductEnricher:
    """Enriches product data with categories and attributes"""
    
    def __init__(self, 
                 taxonomy_dir: Optional[Path] = None,
                 confidence_threshold: float = 0.5):
        """Initialize with taxonomy directory and confidence threshold"""
        self.categorizer = ClothingCategorizer(taxonomy_dir)
        self.mapper = TaxonomyMapper(taxonomy_dir)
        self.confidence_threshold = confidence_threshold
        
    def enrich_product(self, product: Dict) -> EnrichmentResult:
        """Enrich a single product with category and attributes"""
        try:
            # Extract product info
            product_id = product['product_id']
            title = product['title']
            description = product.get('description', '')
            
            # Get suggested attributes (includes category)
            attributes = self.categorizer.get_suggested_attributes(title, description)
            
            if not attributes or 'category' not in attributes:
                return EnrichmentResult(
                    product_id=product_id,
                    errors=["No category found"]
                )
            
            # Extract category info
            category_info = attributes.pop('category')
            
            # Create result
            result = EnrichmentResult(
                product_id=product_id,
                category_id=category_info['gid'],
                category_path=category_info['path'],
                confidence=category_info['confidence'],
                attributes=attributes
            )
            
            # Add debug logging
            logger.debug(f"Category info: {category_info}")
            logger.debug(f"Attributes: {attributes}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error enriching product {product.get('product_id')}: {str(e)}")
            return EnrichmentResult(
                product_id=product.get('product_id'),
                errors=[str(e)]
            )
    
    def format_graphql_payload(self, result: EnrichmentResult) -> Optional[Dict]:
        """
        Format enrichment result as GraphQL mutation payload
        Returns None if result is invalid
        """
        if not result.is_valid:
            logger.warning(
                f"Cannot format invalid enrichment result for {result.product_id}. "
                f"Errors: {result.errors}"
            )
            return None
            
        try:
            return self.mapper.format_graphql_input(
                product_id=result.product_id,
                category_id=result.category_id,
                attributes=result.attributes
            )
        except Exception as e:
            logger.error(f"Error formatting GraphQL payload: {str(e)}")
            return None
    
    def batch_enrich_products(self, products: List[Dict], skip_low_confidence: bool = True) -> Tuple[List[Dict], List[Dict]]:
        """Enrich multiple products"""
        successful = []
        failed = []
        
        for product in products:
            try:
                # Get enrichment data
                attributes = self.categorizer.get_suggested_attributes(
                    product['title'],
                    product.get('description', ''),
                    product  # Pass the full product object
                )
                
                if not attributes:
                    failed.append(product)
                    continue
                    
                # Format payload
                payload = {
                    'id': product['product_id'],
                    'category': attributes.pop('category')['gid']  # Remove category and get GID
                }
                
                # Add remaining attributes
                payload.update(attributes)  # Add all other attributes directly
                    
                successful.append(payload)
                
            except Exception as e:
                logger.error(f"Failed to enrich product {product.get('title')}: {str(e)}")
                failed.append(product)
                
        return successful, failed

    def get_product_attributes(self, product: Dict) -> Dict:
        """Get suggested attributes for a product"""
        # Get category first
        category_id, confidence = self.categorizer.categorize(
            product['title'],
            product.get('description', '')
        )
        
        if not category_id:
            logger.warning("No category found")
            return {}
        
        # Get category path
        category_path = self.mapper.get_path_from_category_id(category_id)
        
        # Get allowed attributes for category
        allowed_attrs = self.mapper.get_allowed_attribute_ids(category_id)
        logger.debug(f"Allowed attributes: {allowed_attrs}")
        
        # Build attributes dict
        attributes = {
            'category': {
                'gid': category_id,
                'path': category_path,
                'confidence': confidence
            }
        }
        
        # Add attribute values
        for attr_id in allowed_attrs:
            value = self.categorizer._get_attribute_value(
                product['title'],
                product.get('description', ''),
                attr_id,
                product
            )
            if value:
                attributes[attr_id] = value
                logger.debug(f"Added attribute {attr_id}: {value}")
        
        logger.debug(f"Final attributes: {attributes}")
        return attributes

def main():
    """Example usage"""
    enricher = ProductEnricher()
    
    # Test products
    test_products = [
        {
            "product_id": "gid://shopify/Product/123",
            "title": "Classic Cotton Crew Neck T-Shirt",
            "description": "A comfortable short-sleeve tee made from 100% organic cotton."
        },
        {
            "product_id": "gid://shopify/Product/456",
            "title": "Slim Fit Dark Wash Jeans",
            "description": "Premium denim pants with a modern slim cut."
        },
        {
            "product_id": "gid://shopify/Product/789",
            "title": "Mystery Product",  # Should fail confidence check
            "description": "A very vague description"
        }
    ]
    
    # Process batch
    successful, failed = enricher.batch_enrich_products(test_products)
    
    # Print results
    print("\nSuccessful Enrichments:")
    for payload in successful:
        print(f"\nProduct: {payload['id']}")
        print(f"Category: {payload['category']}")
        print("Attributes:")
        for field in payload['metafields']:
            print(f"  {field['key']}: {field['value']}")
    
    print("\nFailed Enrichments:")
    for result in failed:
        print(f"\nProduct: {result['product_id']}")
        print(f"Errors: {result['errors']}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main() 