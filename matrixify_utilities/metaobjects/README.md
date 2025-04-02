# Color Metaobject Generation

## Structure
Color metaobjects include:
- Handle (e.g., `shopify--color-pattern.coral`)
- Display name
- Hex code
- Shopify color taxonomy ID

## Field Mapping
- handle: `shopify--color-pattern.{normalized-name}`
- displayName: Human-readable color name
- hexCode: #RRGGBB format
- taxonomyId: Shopify GID reference

## Generation Logic
1. Extract unique colors from variants
2. Normalize color names
3. Map to Shopify taxonomy
4. Generate metaobject definitions 