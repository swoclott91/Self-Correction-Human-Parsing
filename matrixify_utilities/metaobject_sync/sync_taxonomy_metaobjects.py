import json
import os
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv
import sys
import time

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the ShopifyClient
from matrixify_utilities.api.client import ShopifyClient

# Load environment variables
load_dotenv()

# After the imports, before creating MetaobjectSyncer
print("\n🔍 Debug Environment:")
print(f"Current working directory: {os.getcwd()}")
print(f"Project root: {PROJECT_ROOT}")
print(f".env file exists: {Path('.env').exists()}")
print(f"SHOPIFY_SHOP_URL: {os.getenv('SHOPIFY_SHOP_URL')}")
print(f"SHOPIFY_ACCESS_TOKEN: {'[SET]' if os.getenv('SHOPIFY_ACCESS_TOKEN') else '[NOT SET]'}")

TAXONOMY_DIR = Path("matrixify_utilities/taxonomy_data")
ATTRIBUTES_FILE = TAXONOMY_DIR / "apparel_accessories_attributes.json"
VALUES_FILE = TAXONOMY_DIR / "values.json"
GID_OUTPUT_FILE = Path("matrixify_utilities/metaobject_sync/gid_cache.json")

class MetaobjectSyncer:
    """Syncs taxonomy values to Shopify metaobjects"""
    
    def __init__(self, shop_url: str = None, access_token: str = None):
        """Initialize with shop credentials"""
        self.shop_url = shop_url or os.getenv("SHOPIFY_SHOP_URL")
        self.access_token = access_token or os.getenv("SHOPIFY_ACCESS_TOKEN")
        
        if not self.shop_url or not self.access_token:
            raise ValueError("SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN must be provided either as arguments or environment variables")
        
        self.client = ShopifyClient(
            shop_url=self.shop_url,
            access_token=self.access_token,
            validate_schema=False
        )

    def enable_metaobject_definition(self, handle: str) -> None:
        type_name = f"shopify--{handle}"
        
        result = self.client.execute_query("""
            mutation standardMetaobjectDefinitionEnable($type: String!) {
                standardMetaobjectDefinitionEnable(type: $type) {
                    metaobjectDefinition {
                        id
                        type
                        name
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
        """, variables={"type": type_name})
        
        if "errors" in result or result.get("data", {}).get("standardMetaobjectDefinitionEnable", {}).get("userErrors"):
            print(f"⚠️ Error enabling definition for {type_name}")
            print(result)
        else:
            print(f"✅ Enabled definition: {type_name}")

    def get_existing_metaobjects(self, type_name: str) -> Dict:
        print(f"\n🔍 Checking existing metaobjects for type: {type_name}")
        
        result = self.client.execute_query("""
            query GetMetaobjects($type: String!) {
                metaobjects(first: 100, type: $type) {
                    edges {
                        node {
                            id
                            handle
                            fields {
                                key
                                value
                            }
                        }
                    }
                }
            }
        """, variables={"type": type_name})
        
        print(f"\n🔍 Debug: Raw API Response:")
        print(json.dumps(result, indent=2))
        
        if "errors" in result:
            print(f"⚠️ Query error: {result['errors']}")
            return {}

        try:
            # The response has the data directly in the root
            edges = result.get("metaobjects", {}).get("edges", [])
            print(f"\n🔍 Debug: Found {len(edges)} edges")
            
            existing_map = {}
            
            print("\n🔍 Debug: Processing metaobjects:")
            for edge in edges:
                node = edge["node"]
                print(f"\n   Processing node: {node['handle']}")
                
                # Convert fields array to dictionary
                fields = {field["key"]: field["value"] for field in node["fields"]}
                
                # Get taxonomy reference and extract ID
                taxonomy_ref = fields.get("taxonomy_reference", "")
                if taxonomy_ref:
                    taxonomy_id = taxonomy_ref.split("/")[-1]
                    print(f"   Found taxonomy ID: {taxonomy_id} for handle: {node['handle']}")
                    
                    # Store in map
                    existing_map[taxonomy_id] = {
                        "id": node["id"],
                        "handle": node["handle"],
                        "fields": fields
                    }
                    print(f"   ✅ Mapped taxonomy_id {taxonomy_id} -> {node['handle']}")
            
            print(f"\n🔍 Debug: Final map contains {len(existing_map)} entries:")
            for tax_id, info in existing_map.items():
                print(f"   • {tax_id}: {info['handle']} ({info['id']})")
            
            return existing_map
            
        except Exception as e:
            print(f"⚠️ Error processing response: {str(e)}")
            return {}

    def create_metaobject(self, type_name: str, handle: str, fields: Dict) -> Optional[Dict]:
        print(f"\n📝 Creating metaobject:")
        print(f"   Type: {type_name}")
        print(f"   Handle: {handle}")
        print(f"   Fields: {json.dumps(fields, indent=2)}")
        
        # Ensure type has shopify-- prefix
        if not type_name.startswith("shopify--"):
            type_name = f"shopify--{type_name}"
        
        variables = {
            "metaobject": {
                "type": type_name,
                "handle": handle,
                "fields": [
                    {"key": "label", "value": fields["name"]},
                    {
                        "key": "taxonomy_reference", 
                        "value": (f"gid://shopify/TaxonomyValue/{fields['taxonomy_value_id']}" 
                                 if not fields['taxonomy_value_id'].startswith("gid://") 
                                 else fields['taxonomy_value_id'])
                    }
                ]
            }
        }
        
        print(f"   Variables: {json.dumps(variables, indent=2)}")
        
        try:
            result = self.client.execute_query("""
                mutation metaobjectCreate($metaobject: MetaobjectCreateInput!) {
                    metaobjectCreate(metaobject: $metaobject) {
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
            """, variables=variables)
            
            print(f"   Response: {json.dumps(result, indent=2)}")
            
            if "errors" in result:
                print(f"⚠️ GraphQL Error: {result['errors']}")
                return None
            
            created = result.get("data", {}).get("metaobjectCreate", {})
            if created.get("userErrors"):
                print(f"⚠️ User Errors: {created['userErrors']}")
                return None
            
            return created.get("metaobject")
            
        except Exception as e:
            print(f"⚠️ Exception during creation: {str(e)}")
            return None

    def _build_attribute_map(self, attributes_data: Dict, values_data: Dict) -> Dict:
        """Build mapping of attributes and their values"""
        attr_map = {}
        
        # First collect all unique attributes from the verticals data
        for vertical in attributes_data.get("verticals", []):
            if vertical["name"] == "Apparel & Accessories":
                for category in vertical.get("categories", []):
                    for attr in category.get("attributes", []):
                        handle = attr.get("handle")
                        attr_id = attr.get("id")
                        if handle and attr_id and handle not in attr_map:
                            print(f"   • Found attribute: {handle} (ID: {attr_id})")
                            attr_map[handle] = {
                                "attribute_id": attr_id,
                                "values": []
                            }

        # Debug output
        print(f"\nFound {len(attr_map)} attributes:")
        for handle, data in attr_map.items():
            print(f"   • {handle} (ID: {data['attribute_id']})")

        # Add values to attributes
        for value_id, value in values_data.get("data", {}).items():
            if not isinstance(value, dict):
                print(f"⚠️ Warning: Unexpected value structure for ID {value_id}")
                continue
            
            attr_id = value.get("attribute_id")
            if not attr_id:
                print(f"⚠️ Warning: No attribute_id for value {value_id}")
                continue

            # Find matching attribute by ID
            for handle, attr in attr_map.items():
                if attr["attribute_id"] == attr_id:
                    # Get just the value part after the __ separator
                    full_handle = value.get("handle", "")
                    value_handle = full_handle.split("__")[-1] if "__" in full_handle else full_handle
                    
                    attr["values"].append({
                        "name": value.get("name", "Unknown"),
                        "handle": value_handle,  # Use just the value part
                        "taxonomy_value_id": value_id.split("/")[-1]  # Extract ID from GID
                    })
                    print(f"   • Added value: {value_handle} to {handle}")
                    break

        return attr_map

    def sync_all(self):
        """Sync all taxonomy values to metaobjects"""
        # Load taxonomy data
        with open(ATTRIBUTES_FILE) as f:
            attributes = json.load(f)
        with open(VALUES_FILE) as f:
            values = json.load(f)

        attr_map = self._build_attribute_map(attributes, values)

        gid_map = {}
        stats = {
            "enabled": 0,
            "created": 0,
            "existing": 0,
            "errors": 0,
            "skipped": 0
        }

        skip_attributes = {"color", "color-pattern", "pattern"}

        for handle, attr in attr_map.items():
            if handle in skip_attributes:
                print(f"\n⏭️ Skipping attribute: {handle} (will be handled separately)")
                stats["skipped"] += 1
                continue

            print(f"\n▶️ Syncing attribute: {handle}")
            
            # Enable definition first
            try:
                self.enable_metaobject_definition(handle)
                stats["enabled"] += 1
            except Exception as e:
                print(f"⚠️ Failed to enable definition for {handle}: {e}")
                stats["errors"] += 1
                continue

            gid_map[handle] = {}
            type_name = f"shopify--{handle}"

            # Get existing metaobjects
            try:
                existing_map = self.get_existing_metaobjects(type_name)
            except Exception as e:
                print(f"⚠️ Failed to fetch existing metaobjects: {e}")
                stats["errors"] += 1
                continue

            # Process values
            for value in attr["values"]:
                taxonomy_id = value["taxonomy_value_id"]
                print(f"\n🔍 Debug: Processing value:")
                print(f"   Handle: {value['handle']}")
                print(f"   Taxonomy ID: {taxonomy_id}")
                print(f"   Existing map keys: {list(existing_map.keys())}")
                
                # Check if a metaobject already exists for this taxonomy value
                if taxonomy_id in existing_map:
                    existing = existing_map[taxonomy_id]
                    print(f"   ✅ Found match in existing_map:")
                    print(f"      Existing ID: {existing['id']}")
                    print(f"      Existing handle: {existing['handle']}")
                    print(f"      Existing fields: {json.dumps(existing['fields'], indent=2)}")
                    
                    print(f"   ℹ️ Found existing: {handle}/{existing['handle']} for taxonomy ID {taxonomy_id}")
                    gid_map[handle][value["handle"]] = existing["id"]
                    stats["existing"] += 1
                    continue
                else:
                    print(f"   ⚠️ No existing metaobject found for taxonomy_id={taxonomy_id}")
                    # Create new metaobject
                    try:
                        fields = {
                            "name": value["name"],
                            "taxonomy_value_id": taxonomy_id
                        }
                        
                        result = self.create_metaobject(type_name, value["handle"], fields)
                        if result:
                            created_id = result["id"]
                            created_handle = result["handle"]
                            print(f"   ✅ Created new: {handle}/{created_handle} ({created_id}) for taxonomy ID {taxonomy_id}")
                            gid_map[handle][value["handle"]] = created_id
                            stats["created"] += 1
                        else:
                            print(f"   ⚠️ Failed to create: {handle}/{value['handle']}")
                            stats["errors"] += 1

                        time.sleep(0.5)  # Rate limiting

                    except Exception as e:
                        print(f"⚠️ Exception creating metaobject: {str(e)}")
                        print(f"   Value data: {json.dumps(value, indent=2)}")
                        stats["errors"] += 1

            # Write progress after each attribute
            GID_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(GID_OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(gid_map, f, indent=2)

        # Final summary
        print("\n📊 Sync Summary:")
        print(f"   • Attributes skipped: {stats['skipped']}")
        print(f"   • Attributes enabled: {stats['enabled']}")
        print(f"   • Metaobjects created: {stats['created']}")
        print(f"   • Existing metaobjects: {stats['existing']}")
        print(f"   • Errors encountered: {stats['errors']}")
        print(f"   • Total values synced: {stats['created'] + stats['existing']}")
        print(f"\n✅ GID cache written to {GID_OUTPUT_FILE}")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    try:
        syncer = MetaobjectSyncer()
        syncer.sync_all()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
