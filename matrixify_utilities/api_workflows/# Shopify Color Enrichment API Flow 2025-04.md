# Shopify Color Enrichment API Flow (2025-04)

This document outlines the full pipeline to enrich product variants with seasonal color palette and color metaobject assignments.
With running venv:

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
python -m matrixify_utilities.api_workflows.analyze_and_enrich_colors_api


Analyze hex code: python -m matrixify_utilities.scripts.analyze_hex_color 79a8c8

## Overview

This process analyzes product variant images, detects dominant colors, assigns seasonal palettes, and connects Shopify taxonomy + metaobject data back to each variant and product option value.

---

## 🔁 Full API Workflow

### 1. Fetch Product Variants
- **Input**: DRAFT status products (via `VariantSource`)
- **Data pulled**:
  - `product_id`
  - `color_option_id`, `color_option_value_id`
  - `image_url`, `image_alt`
  - `variant_ids`

---

### 2. Download & Analyze Garment Image
- Use `GarmentParser` to parse segmentation mask.
- Use `ColorNormalizer.color_extractor` to extract dominant colors.
- Top 1 color is used for classification.

---

### 3. Classify Seasonal Palette
- Input: dominant color (RGB/HEX)
- Output: best seasonal match (e.g., `Soft Summer`) with explanation.
- Mapped to `PALETTE_METAOBJECTS` to get Shopify metaobject GID.

---

### 4. Map to Shopify Color Taxonomy
- Use `map_to_shopify_color(label, hex)`
- Returns: `gid://shopify/TaxonomyValue/...`

---

### 5. Create or Reuse Color Metaobject
- Unique handle: `"{color-label}-{hex}"`
- Type: `shopify--color-pattern`
- Fields:
  - `label` = display name
  - `color` = hex value
  - `color_taxonomy_reference` = list of color taxonomy GIDs
  - `pattern_taxonomy_reference` = always solid `gid://shopify/TaxonomyValue/2874`
- Checks for existing metaobject using `metaobjectByHandle()`.

---

### 6. Assign Season Palette to Variants
- For each variant:
  - Assign metafield:
    - `namespace: custom`
    - `key: pallet`
    - `type: list.metaobject_reference`
    - `value: [palette_gid]`

---

### 7. Attach Color Metaobject to Product Option Value
- Fetch `product.options` to get:
  - `option_id` for Color
  - All `optionValues` with GIDs
- Match current color name → get `option_value_id`
- Mutation: `productOptionUpdate`
  - Link `color-pattern` metafield to "Color" option
  - Assign `linkedMetafieldValue` to the matched value

---

## Notes

- All product IDs must use `gid://shopify/Product/...` format.
- Make sure metafield definitions (`color-pattern`, `pallet`) exist.
- The `linkedMetafield` on the product option is required before linking values.
- Be kind to Shopify API: `time.sleep(0.5)` after heavy operations.

---

## ✅ Status Checks (Per Product)
- [x] Color metaobject created or reused?
- [x] Seasonal palette metafield assigned to variants?
- [x] Color metaobject attached to correct option value?