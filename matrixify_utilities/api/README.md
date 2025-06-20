# API Module – Shopify Taxonomy Integration

This module provides the core functionality for updating Shopify product categories and attributes using the **2025-04 Admin API** and the official **Shopify Standard Product Taxonomy**.

---

## 📁 Directory Overview

```
api/
├── client.py               # Core API functionality
├── graphql_mutations.py    # GraphQL mutation builders
├── category_updater.py     # High-level product update handler
└── README.md               # This file
```

---

## 🔧 Shopify API Integration

### API Version
- **Admin API version**: `2025-04`
- **GraphQL Endpoint**:  
  `https://{your-store}.myshopify.com/admin/api/2024-04/graphql.json`

---

## 🏷️ Category ID Format

Shopify now uses **GIDs** (Global IDs) to reference categories.  
Example formats:

- `gid://shopify/TaxonomyCategory/aa` → Apparel & Accessories  
- `gid://shopify/TaxonomyCategory/aa-1` → Shirts & Tops (subcategory)

Category GIDs are required for product updates.

---

## 🛠️ GraphQL Mutation: `productUpdate`

### Mutation Format

```graphql
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
```

### Variables Format

```json
{
  "input": {
    "id": "gid://shopify/Product/1234567890",
    "category": "gid://shopify/TaxonomyCategory/aa"
  }
}
```

Use the **full GID** for both the product and category.

---

## ❗ Important Notes

- ✅ `category` is the new field (replaces deprecated `productCategory`)
- ✅ IDs **must** use the `gid://` format
- ✅ Use `TaxonomyCategory` — **not** `ProductTaxonomyNode`
- ✅ You must be using **Admin API v2024-04** or later

---

## ❌ Deprecated Features (Do Not Use)

- `productCategory` field
- Numeric category IDs
- `ProductTaxonomyNode` type
- `queryRoot.productTaxonomy`
- `queryRoot.productTaxonomyNodes`

---

## 🧪 Example Function (Python)

```python
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
        userErrors {
          field
          message
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
    # Call Shopify GraphQL API with client.post(mutation, variables)
```

---

## 🧩 Related Files in Repository

- `download_taxonomy.py` → Downloads taxonomy from Shopify GitHub
- `test_taxonomy_update.py` → Validates sample category assignments
- `taxonomy_mapper.py` → Loads and maps taxonomy references from JSON

---

## 📚 Documentation Reference

[Shopify Admin API (2025-04) – Product Object](https://shopify.dev/docs/api/admin-graphql/latest/objects/Product#field-product-category)

---
