# Shopify API Integration

## Components

### ShopifyClient (`client.py`)
Core API functionality including:
- Authentication
- GraphQL queries
- Rate limiting
- Error handling

### CategoryUpdater (`category_updater.py`)
Category-specific operations:
- Product category updates
- Category queries
- Taxonomy integration

## Usage

```python
from api import ShopifyClient, CategoryUpdater

# Initialize
client = ShopifyClient()
category_updater = CategoryUpdater(client)

# Update product category
result = category_updater.update_category(
    product_id="123",
    category_id="gid://shopify/TaxonomyCategory/aa-1-13-1"
)
```

## Configuration
The client uses these credentials in order:
1. Constructor parameters
2. Environment variables
3. Default test credentials
## Category Updates (2024-04)

The latest Shopify Admin API (2024-04) uses a new taxonomy system for product categories. This version introduces several important changes to how categories are handled.

### API Version
- Using Admin API version: `2024-04`
- Endpoint: `https://{shop-name}.myshopify.com/admin/api/2024-04/graphql.json`

### Category ID Format
Categories are now identified using Global IDs (GIDs) in the format:


Example:
- `gid://shopify/TaxonomyCategory/aa` (Apparel & Accessories)
- `gid://shopify/TaxonomyCategory/aa-1` (Subcategory)

### Updating Product Categories

#### GraphQL Mutation

graphql
gid://shopify/TaxonomyCategory/{category-code}


Example:
- `gid://shopify/TaxonomyCategory/aa` (Apparel & Accessories)
- `gid://shopify/TaxonomyCategory/aa-1` (Subcategory)

### Updating Product Categories

#### GraphQL Mutation

graphql
mutation productUpdate($input: ProductInput!) {
productUpdate(input: $input) {
product {
id
title
category {
id
name
fullName
}
}
userErrors {
field
message
}
}
}


#### Variables Format

json
{
"input": {
"id": "gid://shopify/Product/1234567890",
"category": "gid://shopify/TaxonomyCategory/aa"
}
}


### Important Notes
1. The new taxonomy API replaces the deprecated `productCategory` field with `category`
2. Category IDs must be full GIDs, not numeric IDs
3. The `TaxonomyCategory` type replaces the old `ProductTaxonomyNode` type

### Example Usage

python
def update_product_category(product_id: str, category_id: str):
mutation = """
mutation productUpdate($input: ProductInput!) {
productUpdate(input: $input) {
product {
id
category {
id
name
}
}
}
}
"""
variables = {
"input": {
"id": product_id,
"category": category_id
}
}
# Make API call...


### Deprecated Features
The following features are deprecated and should not be used:
- `productCategory` field
- Numeric category IDs
- `ProductTaxonomyNode` type
- `queryRoot.productTaxonomy`
- `queryRoot.productTaxonomyNodes`

### Related Files
- `download_taxonomy.py`: Downloads complete taxonomy structure
- `test_taxonomy_update.py`: Tests category updates
- `taxonomy_mapper.py`: Maps between different category formats

For more information, see the [Shopify Admin API Documentation](https://shopify.dev/docs/api/admin-graphql/2024-04/objects/Product#field-product-category).

# Data Processing Components

## Taxonomy Mapping

The `TaxonomyMapper` class provides functionality to work with Shopify's product taxonomy. It uses the official Shopify taxonomy data from their [product-taxonomy repository](https://github.com/Shopify/product-taxonomy).

### Features
- Downloads and caches the latest taxonomy data
- Maps between category paths and Shopify Global IDs (GIDs)
- Handles category hierarchy and subcategories
- Provides metadata about categories

### Usage Example

python
from matrixify_utilities.scripts.taxonomy_mapper import TaxonomyMapper
Initialize mapper
mapper = TaxonomyMapper()
Get category ID from path
category_id = mapper.get_category_id("Apparel & Accessories")
Returns: "gid://shopify/TaxonomyCategory/aa"
Get path from category ID
path = mapper.get_category_path("gid://shopify/TaxonomyCategory/aa")
Returns: "Apparel & Accessories"
List subcategories
subcats = mapper.list_categories("Apparel & Accessories")


### File Structure
- `categories.txt`: Cached taxonomy data from Shopify
- `processed_taxonomy.json`: Processed mapping data
