import logging
from typing import Dict, List, Optional, Tuple
from .client import ShopifyClient
from scripts.normalize_categories import CategoryNormalizer

logger = logging.getLogger(__name__)

class ProductCategoryProcessor:
    def __init__(self, client: ShopifyClient):
        self.client = client
        self.normalizer = CategoryNormalizer()
        
    def process_all_products(
        self, 
        batch_size: int = 50, 
        dry_run: bool = True,
        progress_callback: Optional[callable] = None,
        product_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Tuple[int, int]:
        """Process and normalize product categories
        
        Args:
            batch_size: Number of products to process per batch
            dry_run: If True, don't make any changes
            progress_callback: Optional callback to update progress
            product_id: Optional specific product ID to process
            limit: Optional maximum number of products to process
            
        Returns:
            Tuple of (processed_count, category_updates)
        """
        processed = 0
        category_updates = 0
        
        try:
            # Get products (single or batch)
            if product_id:
                product = self.client.get_product(product_id)
                if product:
                    products_batch = [product]
                else:
                    logger.error(f"Product with ID {product_id} not found")
                    return 0, 0
            else:
                products_batch = []
                for batch in self.client.get_products_batch(batch_size):
                    products_batch.extend(batch)
                    if limit and len(products_batch) >= limit:
                        products_batch = products_batch[:limit]
                        break

            # Process each product
            for product in products_batch:
                if not product:
                    continue
                    
                logger.info(f"Processing product: {product.get('title')} ({product.get('handle')})")
                
                # Get current category and product details
                current_category = self.client.get_product_category(product.get('id'))
                title = product.get('title', '')
                description = product.get('description', '')
                
                # Try to infer category from title if missing
                if not current_category:
                    normalized_category = self.normalizer.normalize_category(
                        '',  # No existing category
                        title=title,
                        description=description
                    )
                    logger.info(f"Inferred category '{normalized_category}' for product '{title}'")
                    current_category = normalized_category
                else:
                    # Normalize existing category with text context
                    normalized_category = self.normalizer.normalize_category(
                        current_category,
                        title=title,
                        description=description
                    )
                
                # Normalize category
                if normalized_category and normalized_category != current_category:
                    if not dry_run:
                        # Update product category
                        success = self.client.update_product_category(
                            product.get('id'),
                            normalized_category
                        )
                        if success:
                            category_updates += 1
                            logger.info(f"Updated category from '{current_category}' to '{normalized_category}'")
                        else:
                            logger.error(f"Failed to update category for product {product.get('handle')}")
                    else:
                        logger.info(f"Would update category from '{current_category}' to '{normalized_category}' (dry run)")
                
                processed += 1
                if progress_callback:
                    progress_callback()
                    
                logger.info(f"Completed processing product: {product.get('handle')}")
                
            return processed, category_updates
            
        except Exception as e:
            logger.error(f"Error processing products: {e}")
            return 0, 0 