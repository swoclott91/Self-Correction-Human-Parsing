# Processing Scripts

Each script handles one step in the enrichment pipeline:

## Core Scripts

### normalize_sizes.py
- Maps variant size options to standard metafield references
- Input: Raw Matrixify export
- Output: CSV with normalized size metafields

### assign_shopify_category.py
- Assigns Shopify taxonomy Product Category IDs
- Uses product titles and types for mapping
- Output: CSV with category assignments

### extract_variant_colors.py
- Downloads and analyzes variant images
- Uses garment segmentation for accurate color extraction
- Output: CSV with color data (LAB, hex)

### assign_color_metaobjects.py
- Generates standardized color handles
- Maps colors to Shopify taxonomy
- Output: CSV with color metafield references

### assign_palette_metafields.py
- Classifies colors into seasonal palettes
- Assigns palette metafields
- Output: CSV with palette assignments

### generate_metaobjects.py
- Creates color metaobject definitions
- Output: Metaobject import CSV

### combine_all_updates.py
- Merges enriched data
- Validates field formatting
- Output: Final Matrixify import CSV

### validate_csv_integrity.py
- Pre-upload validation
- Checks all required fields
- Reports any formatting issues

### debug_variant.py
- Single variant inspection
- Shows full processing chain
- Useful for troubleshooting 