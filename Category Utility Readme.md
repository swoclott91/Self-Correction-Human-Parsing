# Category & Attribute Utility

A utility for automatically categorizing products and enriching them with attributes based on their titles and descriptions.

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install package in editable mode
pip install -e .

## Core Components

- `clothing_categorizer.py` - Main categorization logic using pattern matching and weighted scoring
- `taxonomy_mapper.py` - Maps between category/attribute names and their Shopify GIDs
- `metaobject_helper.py` - Handles metaobject operations with Shopify
- `update_shopify_category_and_attributes.py` - Main script for updating products

## Usage

### Test Run (Debug Mode)
Test categorization on a small batch of draft products:

powershell
python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status draft --limit 50 --debug

python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status draft --limit 50 --update

python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status draft --limit 50 --update

python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status draft --limit 50 --uncategorized --update

python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status active --limit 1500 --batch-size 100 --uncategorized --update --debug
python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status active --limit 1500 --batch-size 100 --update --debug


python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status active --limit 1500 --batch-size 100 --uncategorized --update --debug

### Update All Products
Process and update all published products:

powershell
python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --update


### Batch Processing
Process large numbers of products in batches:

powershell
python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status draft --limit 800 --batch-size 100 --update

python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status active --limit 1500 --batch-size 100 --update

## Command Line Arguments

- `--status` - Filter products by status (draft/published)
- `--limit` - Maximum number of products to process
- `--batch-size` - Number of products to process in each batch
- `--debug` - Enable debug logging
- `--update` - Actually perform updates (otherwise dry-run)
- `--uncategorized` - Only process products without categories

## Usage Examples

Test uncategorized draft products:

python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status draft --limit 25 --uncategorized --update

Update all draft products (including already categorized):
python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status draft --limit 50 --update

```

This gives you the flexibility to:
1. Process only uncategorized products with `--uncategorized`
2. Process all products without the flag
3. Combine with other filters like `--status` and `--limit`


## How It Works

1. **Product Retrieval**
   - Fetches products from Shopify based on specified filters
   - Can handle both draft and published products

2. **Categorization**
   - Uses pattern matching with weighted scoring
   - Handles clear indicators with high confidence
   - Falls back to detailed pattern matching for edge cases

3. **Attribute Enrichment**
   - Extracts attributes like fabric, neckline, sleeve length
   - Maps attributes to Shopify metaobject values

4. **Update Process**
   - Batches updates for efficiency
   - Uses GraphQL for atomic updates
   - Maintains local cache to minimize API calls

## Files Overview

- `update_category_and_local_cache_attributes.py` - Local cache management
- `update_shopify_categories_only.py` - Category-only updates
- `sync_taxonomy_metaobjects.py` - Syncs taxonomy definitions
- `graphql_update_test.py` - Tests for GraphQL operations

## Future Improvements

1. **Categorization**
   - Add machine learning model for edge cases
   - Expand pattern library for new product types
   - Add support for more languages

2. **Performance**
   - Implement parallel processing for batches
   - Add bulk update capabilities
   - Optimize cache management

3. **Features**
   - Add support for custom attributes
   - Implement category suggestions
   - Add validation rules engine

4. **Monitoring**
   - Add detailed success/failure reporting
   - Implement change tracking
   - Add performance metrics

## Notes

- Always test with `--debug` flag first
- Use appropriate batch sizes based on API limits
- Keep local cache in sync with Shopify
- Monitor update success rates
- Back up data before large updates

## Dependencies

- Python 3.7+
- Shopify Admin API access
- GraphQL support
- Local cache storage

## Error Handling

The utility includes robust error handling for:
- API rate limits
- Network issues
- Invalid data
- Cache mismatches

## Maintenance

Regular maintenance tasks:
1. Update pattern libraries
2. Sync taxonomy definitions
3. Clean up local cache
4. Monitor API usage

