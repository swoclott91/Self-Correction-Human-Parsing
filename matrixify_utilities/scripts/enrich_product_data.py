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
        
    def enrich_product(self, 
                      product_id: str,
                      title: str,
                      description: str = "",
                      skip_low_confidence: bool = True) -> EnrichmentResult:
        """
        Enrich a product with category and attribute data
        
        Args:
            product_id: Shopify product ID (with gid:// prefix)
            title: Product title
            description: Product description (optional)
            skip_low_confidence: Skip enrichment if confidence below threshold
            
        Returns:
            EnrichmentResult object containing enrichment data and status
        """
        result = EnrichmentResult(product_id=product_id)
        
        try:
            # Get category and confidence
            category_path, confidence = self.categorizer.categorize(title, description)
            result.category_path = category_path
            result.confidence = confidence
            
            # Check confidence threshold
            if skip_low_confidence and confidence < self.confidence_threshold:
                result.errors.append(
                    f"Low confidence ({confidence:.2f}) below threshold "
                    f"({self.confidence_threshold})"
                )
                return result
            
            # Get category ID
            category_id = self.mapper.get_category_id_from_path(category_path)
            if not category_id:
                result.errors.append(f"Failed to map path to category ID: {category_path}")
                return result
            result.category_id = category_id
            
            # Get suggested attributes
            attributes = self.categorizer.get_suggested_attributes(title, description)
            if not attributes:
                logger.warning(f"No attributes found for product {product_id}")
            result.attributes = attributes
            
            return result
            
        except Exception as e:
            logger.error(f"Error enriching product {product_id}: {str(e)}")
            result.errors.append(f"Enrichment error: {str(e)}")
            return result
    
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
    
    def batch_enrich_products(self, 
                            products: List[Dict],
                            skip_low_confidence: bool = True) -> Tuple[List[Dict], List[Dict]]:
        """
        Enrich multiple products
        
        Args:
            products: List of dicts with product_id, title, description
            skip_low_confidence: Skip products with low categorization confidence
            
        Returns:
            Tuple of (successful_payloads, failed_results)
        """
        successful_payloads = []
        failed_results = []
        
        for product in products:
            try:
                # Enrich product
                result = self.enrich_product(
                    product_id=product['product_id'],
                    title=product['title'],
                    description=product.get('description', ''),
                    skip_low_confidence=skip_low_confidence
                )
                
                # Format payload if valid
                if result.is_valid:
                    payload = self.format_graphql_payload(result)
                    if payload:
                        successful_payloads.append(payload)
                    else:
                        failed_results.append(result.to_dict())
                else:
                    failed_results.append(result.to_dict())
                    
            except Exception as e:
                logger.error(f"Error processing product {product.get('product_id')}: {str(e)}")
                failed_results.append({
                    'product_id': product.get('product_id'),
                    'errors': [str(e)]
                })
                
        return successful_payloads, failed_results

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