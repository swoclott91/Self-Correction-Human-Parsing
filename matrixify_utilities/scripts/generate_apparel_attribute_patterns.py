import json
import re
from pathlib import Path

# Paths
data_dir = Path("matrixify_utilities/taxonomy_data")
attributes_path = data_dir / "attributes.json"
values_path = data_dir / "values.json"
categories_path = data_dir / "categories.json"
output_path = Path("matrixify_utilities/scripts/clothing_categorizer_patterns.py")

# Load data
with attributes_path.open("r", encoding="utf-8") as f:
    attributes_data = json.load(f)["data"]

with values_path.open("r", encoding="utf-8") as f:
    values_data = json.load(f)["data"]

with categories_path.open("r", encoding="utf-8") as f:
    categories_data = json.load(f)["data"]

# Collect allowed attributes for Apparel & Accessories vertical
allowed_attributes = set()
for category in categories_data.values():
    if category.get("vertical") == "Apparel & Accessories":
        allowed_attributes.update(category.get("allowed_attributes", []))

# Map attribute GIDs to handles (filtered by vertical)
handle_for_gid = {
    gid: attr["handle"]
    for gid, attr in attributes_data.items()
    if attr.get("handle") and gid in allowed_attributes
}

# Generate regex patterns
attribute_patterns = {}

for value in values_data.values():
    attr_gid = value.get("attribute_id")
    attr_handle = handle_for_gid.get(attr_gid)
    if not attr_handle:
        continue

    if attr_handle not in attribute_patterns:
        attribute_patterns[attr_handle] = {}

    name = value["name"]
    cleaned = re.sub(r"[^a-zA-Z0-9 ]", "", name).strip().lower()
    parts = re.escape(cleaned).split(r"\ ")
    flexible_pattern = r"[\s\-]?".join(parts)
    word_pattern = r"\b" + flexible_pattern + r"s?\b"
    attribute_patterns[attr_handle][name] = word_pattern

# Save result
script_content = f'''import re

ATTRIBUTE_PATTERNS = {json.dumps(attribute_patterns, indent=2)}
'''

output_path.write_text(script_content, encoding="utf-8")

print(f"✅ Saved {len(attribute_patterns)} attribute pattern groups to: {output_path}")
