# Shopify Color Pattern Metaobject Creation Guide

This document explains how to correctly create and structure `shopify--color-pattern` metaobjects in Shopify using the 2025-04 GraphQL Admin API. It covers field types, data requirements, and common errors with solutions.

---

## 🎯 Objective

To create a new color pattern metaobject with:
- A human-readable label
- A hex color value
- A color reference tied to Shopify's **product taxonomy**
- A pattern reference also tied to Shopify's **product taxonomy**

---

## ✅ Required Metaobject Fields

| Field Key                  | Type                                      | Required | Notes                                                  |
|---------------------------|-------------------------------------------|----------|--------------------------------------------------------|
| `label`                   | `TEXT / single_line_text_field`           | ✅       | Display name (e.g., "Soft Rose")                      |
| `color`                   | `COLOR`                                   | ✅       | Hex code (e.g., `#C58C8C`)                            |
| `color_taxonomy_reference`| `REFERENCE / list.product_taxonomy_value_reference` | ✅       | **JSON stringified array** of one or more ProductTaxonomyValue GIDs |
| `pattern_taxonomy_reference`| `REFERENCE / product_taxonomy_value_reference`     | ✅       | **Single ProductTaxonomyValue GID** (not in a list)   |

---

## 🛠️ Working GraphQL Mutation Example

```graphql
mutation {
  metaobjectCreate(metaobject: {
    type: "shopify--color-pattern",
    fields: [
      { key: "label", value: "Soft Rose" },
      { key: "color", value: "#C58C8C" },
      { key: "color_taxonomy_reference", value: "[\"gid://shopify/ProductTaxonomyValue/11\"]" },
      { key: "pattern_taxonomy_reference", value: "gid://shopify/ProductTaxonomyValue/2874" }
    ]
  }) {
    metaobject {
      id
      handle
    }
    userErrors {
      field
      message
    }
  }
}
