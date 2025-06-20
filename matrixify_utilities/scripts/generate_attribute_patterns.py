import json
import re
from pathlib import Path

taxonomy_path = Path("matrixify_utilities/taxonomy_data/categories.json")

with taxonomy_path.open("r", encoding="utf-8") as f:
    taxonomy_data = json.load(f)

attribute_patterns = {}

for category_data in taxonomy_data["data"].values():
    # Only process Apparel & Accessories categories
    if category_data.get("vertical") != "Apparel & Accessories":
        continue
        
    attribute_info = category_data.get("attribute_info", {})
    for attr in attribute_info.values():
        handle = attr.get("handle")
        values = attr.get("values", [])
        
        if not handle or not values:
            continue  # Skip attributes without values
        
        if handle not in attribute_patterns:
            attribute_patterns[handle] = {}
        
        for value in values:
            name = value["name"]
            cleaned = re.sub(r"[^a-zA-Z0-9 ]", "", name).strip().lower()
            # Properly build the regex pattern
            parts = re.escape(cleaned).split(r"\ ")
            flexible_pattern = r"[\s\-]?".join(parts)
            word_pattern = r"\b" + flexible_pattern + r"s?\b"
            attribute_patterns[handle][name] = word_pattern

# Print statistics
non_empty = {k: v for k, v in attribute_patterns.items() if v}
print(f"Found {len(non_empty)} non-empty attribute groups (out of {len(attribute_patterns)})")

# Save the Python module to file
output_path = Path("matrixify_utilities/scripts/clothing_categorizer_patterns.py")
script_content = f'''import re

ATTRIBUTE_PATTERNS = {json.dumps(attribute_patterns, indent=2)}
'''

output_path.write_text(script_content, encoding="utf-8")

print(f"\n✅ Saved attribute patterns to: {output_path}")
