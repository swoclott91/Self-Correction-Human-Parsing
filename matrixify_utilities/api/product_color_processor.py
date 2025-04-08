import logging
from typing import Dict, List, Optional, Tuple
from .client import ShopifyClient
from .color_metaobject_creator import ColorMetaobjectCreator
from .metaobject_registry import MetaobjectRegistry
from utils.palette_classifier import PaletteClassifier

logger = logging.getLogger(__name__)

class ProductColorProcessor:
    def __init__(self, client: ShopifyClient, registry: Optional[MetaobjectRegistry] = None):
        self.client = client
        self.registry = registry or MetaobjectRegistry()
        self.palette_classifier = PaletteClassifier()
        self.color_creator = ColorMetaobjectCreator(client, registry)
        
    def process_all_products(
        self, 
        batch_size: int = 50, 
        dry_run: bool = True,
        progress_callback: Optional[callable] = None,
        product_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Tuple[int, int, int]:
        """Process products from Shopify API
        
        Args:
            batch_size: Number of products to process per batch
            dry_run: If True, don't make any changes
            progress_callback: Optional callback to update progress
            product_id: Optional specific product ID to process
            limit: Optional maximum number of products to process
            
        Returns:
            Tuple of (processed_count, color_objects_created, connections_made)
        """
        processed = 0
        colors_created = 0
        connections = 0
        
        try:
            # Get products (single or batch)
            if product_id:
                product = self.client.get_product(product_id)
                if product:
                    products_batch = [product]
                else:
                    logger.error(f"Product with ID {product_id} not found")
                    return 0, 0, 0
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
                
                # Find color option
                options = product.get('options', [])
                color_option = next(
                    (opt for opt in options 
                     if isinstance(opt, dict) and opt.get('name', '').lower() == 'color'),
                    None
                )
                if not color_option:
                    continue
                
                # Get variants
                variants = product.get('variants', {}).get('nodes', [])
                if not variants:
                    continue
                
                # Process each unique color
                processed_colors = {}  # Map of color_value -> first variant with that color
                for variant in variants:
                    if not variant:
                        continue
                        
                    # Get color value
                    selected_options = variant.get('selectedOptions', [])
                    color_value = next(
                        (opt.get('value') for opt in selected_options
                         if isinstance(opt, dict) and opt.get('name', '').lower() == 'color'),
                        None
                    )
                    
                    # Store first variant of each color
                    if color_value and color_value not in processed_colors:
                        processed_colors[color_value] = variant
                
                # Process each unique color variant
                for color_value, variant in processed_colors.items():
                    image = variant.get('image', {})
                    if not image:
                        continue
                        
                    image_url = image.get('url')
                    if not image_url:
                        continue
                        
                    # Analyze color
                    color_results = self.palette_classifier.classify_image_urls_batch([image_url])
                    color_season = color_results.get(image_url)
                    
                    if not color_season:
                        logger.warning(f"No color analysis for {image_url}")
                        continue
                    
                    # Create color metaobject if needed
                    color_handle = f"color-{color_value.lower().replace(' ', '-')}"
                    color_data = {
                        'handle': color_handle,
                        'name': color_value,
                        'season': color_season.season.value,
                        'confidence': color_season.confidence,
                        'explanation': color_season.explanation
                    }
                    
                    if not dry_run:
                        # Create/get color metaobject
                        created = self.color_creator.create_color_metaobjects([color_data])
                        if created[0]:
                            colors_created += 1
                            logger.info(f"Created new color metaobject: {color_handle}")
                        
                        # Get metaobject ID
                        color_id = self.client.get_color_metaobject_id(color_handle)
                        if not color_id:
                            logger.error(f"Failed to get ID for color: {color_handle}")
                            continue
                            
                        # Connect product
                        if self.client.connect_product_color(product.get('id'), color_id):
                            connections += 1
                            logger.info(f"Connected product to color: {color_handle}")
                            
                            # Connect all variants with this color
                            for v in variants:
                                v_options = v.get('selectedOptions', [])
                                v_color = next(
                                    (opt.get('value') for opt in v_options
                                     if isinstance(opt, dict) and opt.get('name', '').lower() == 'color'),
                                    None
                                )
                                if v_color == color_value:
                                    self.client.connect_variant_color(v.get('id'), color_id)
                                    connections += 1
                
                processed += 1
                if progress_callback:
                    progress_callback()
                
                logger.info(f"Completed processing product: {product.get('handle')}")
                
            return processed, colors_created, connections
            
        except Exception as e:
            logger.error(f"Error processing products: {e}")
            return 0, 0, 0 