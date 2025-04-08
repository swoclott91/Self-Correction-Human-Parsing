# taxonomy_data Directory – Shopify Category & Attribute References

This folder contains all the parsed reference data for Shopify’s official **Standard Product Taxonomy**, downloaded from Shopify’s GitHub repository.

It serves as the canonical source for:
- Product category GIDs
- Category hierarchies
- Valid attributes and values per category

---

## 📁 File Overview

```
taxonomy_data/
├── categories.json    # Complete category tree with GIDs and nesting
├── attributes.json    # Category-specific attributes
├── values.json        # Attribute-specific allowed values
├── fetch_from_github.py  # Fetches and processes the latest taxonomy data
└── README.md          # This file
```

---

## 📚 Shopify Taxonomy Format (2025-06-unstable)

Taxonomy JSON files follow this structure:

```json
{
  "version": "2025-06-unstable",
  "verticals": [
    {
      "name": "Apparel & Accessories",
      "prefix": "aa",
      "categories": [
        {
          "id": "gid://shopify/TaxonomyCategory/aa",
          "name": "Apparel & Accessories",
          "level": 0,
          "children": [
            {
              "id": "gid://shopify/TaxonomyCategory/aa-1",
              "name": "Shirts & Tops"
            },
            ...
          ]
        },
        ...
      ]
    }
  ]
}
```

---

## 🔑 Key Concepts

- **Category GIDs** are required to update products using the Shopify API
- Categories include a list of **attributes** (e.g. sleeve length, neckline)
- Each attribute has valid **values** (e.g. "Short Sleeve", "Crew Neck")

These are used to power **category-specific metafield assignments** in Shopify Admin.

---

## 🧭 Use Cases

### 1. Initial Store Update
Use this data to categorize your entire product catalog (e.g. 1400+ items) using pattern matching or NLP extraction, then submit the updates via the API.

### 2. Ongoing Updates
As you add new products (e.g. via dropshipping or supplier sync), this data ensures you're always assigning categories and metafields according to Shopify's live standard.

---

## 🛠️ `fetch_from_github.py`

This script pulls the latest taxonomy reference files from the Shopify GitHub repository and writes them into:

- `categories.json`
- `attributes.json`
- `values.json`

It also normalizes structures and flattens hierarchical data for easier lookup.

---

## 🚀 Integration

Other modules (like `taxonomy_mapper.py` and `clothing_categorizer.py`) load these reference files to:

- Match product titles/descriptions to GID categories
- Validate attribute assignments
- Generate payloads for the `productUpdate` GraphQL mutation

---

## 🔗 Reference

- Shopify Taxonomy GitHub: [https://github.com/Shopify/product-taxonomy](https://github.com/Shopify/product-taxonomy)
- Taxonomy Docs: [https://shopify.dev/docs/apps/online-store/standard-taxonomy](https://shopify.dev/docs/apps/online-store/standard-taxonomy)

