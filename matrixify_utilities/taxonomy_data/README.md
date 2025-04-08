# taxonomy_data Directory – Shopify Taxonomy Integration Guide

This directory contains the **reference source-of-truth data** for Shopify's Standard Product Taxonomy, which powers category and attribute classification in your Shopify store integration.

It supports both:
- **Initial store-wide updates** (e.g. mapping 1400+ existing products)
- **Ongoing classification of new products** (e.g. from dropshipping feeds)

---

## 📁 Directory Structure

```
taxonomy_data/
├── categories.json          # Parsed category tree (from /verticals[].categories[])
├── attributes.json          # Attributes per category
├── values.json              # Allowed values for each attribute
├── fetch_from_github.py     # Downloads and normalizes taxonomy files from GitHub
└── README.md                # This file
```

---

## 🧠 Data Overview

The files in this folder are downloaded from:
[Shopify's Product Taxonomy GitHub Repo](https://github.com/Shopify/product-taxonomy)

They are updated quarterly and represent a universal structure used by Shopify and many marketplaces.

### 🧱 Shopify JSON Structure

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
          "full_name": "Apparel & Accessories",
          "level": 0,
          "attributes": [],
          "children": [...]
        },
        ...
      ]
    }
  ]
}
```

Key fields:
- `id`: The **Shopify GID** (used in API updates)
- `full_name`: Full nested path (e.g. "Apparel & Accessories > Shirts & Tops")
- `attributes`: List of attribute keys this category supports

---

## 🔄 Workflow Integration

These files support your product classification pipeline:

```mermaid
graph TD
    A[Title/Description] --> B[Categorizer]
    B --> C[category_id (GID)]
    A --> D[Parser]
    D --> E[Attributes & Values]
    C & E --> F[GraphQL Payload Builder]
    F --> G[Shopify API]
```

---

## 🛠️ `fetch_from_github.py`

This script downloads and transforms Shopify’s taxonomy distribution files (`categories.json`, `attributes.json`, `attribute_values.json`) from:

```
https://raw.githubusercontent.com/Shopify/product-taxonomy/main/dist/en/
```

The script:
- Recursively flattens categories under `verticals[].categories`
- Parses attributes and allowed values
- Saves normalized data with version metadata

Sample output:
```json
{
  "version": "2025-06-unstable",
  "updated_at": "...",
  "data": {
    "gid://shopify/TaxonomyCategory/aa": {
      "name": "Apparel & Accessories",
      "path": "Apparel & Accessories",
      "level": 0,
      "children": [...],
      "allowed_attributes": [...]
    }
  }
}
```

---

## 🧩 Supported Use Cases

### ✅ Initial Full Store Update
- Run categorizer/parser over 1000+ products
- Use `full_name` to match known categories
- Convert to `category_id` GID and metafield attributes

### ✅ New Product Drops (Live Imports)
- Categorize and tag as new products arrive
- Parse variant-level attributes (e.g. color, fit, fabric)

---

## 🔗 Developer Notes from Shopify

- Stable releases occur quarterly (CalVer format: `YYYY-MM`)
- Taxonomy includes mapping support to other standards (via `integrations/`)
- Files are published in both `.txt` and `.json` formats
- Translations are available under `localizations/`
- Source-of-truth data lives in `/data`, dist files in `/dist`

See Shopify’s taxonomy README for more:  
[Shopify/product-taxonomy on GitHub](https://github.com/Shopify/product-taxonomy)

---

## 📜 License

Shopify's taxonomy is open-source under the MIT license.
