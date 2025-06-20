import requests
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
import json
import logging

# Load environment variables
load_dotenv("C:/Users/Shane Work/Documents/GitHub/Self-Correction-Human-Parsing/.env")
SHOPIFY_SHOP_URL = os.getenv("SHOPIFY_SHOP_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

SHOPIFY_API_URL = f"https://{SHOPIFY_SHOP_URL}/admin/api/2025-04/graphql.json"

# Fallback metaobject for unassigned colors
UNASSIGNED_COLOR_GID = "gid://shopify/Metaobject/216221352308"  # Replace with your actual unassigned color metaobject

class MetafieldWriter:
    def __init__(self):
        self.endpoint = SHOPIFY_API_URL
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        }

    def get_product_option_values(self, product_id: str, option_id: str) -> List[Dict]:
        """Get all option values for a specific product option"""
        query = {
            "query": f"""
            query {{
              product(id: "{product_id}") {{
                option(id: "{option_id}") {{
                  id
                  name
                  values
                  linkedMetafield {{
                    namespace
                    key
                  }}
                  optionValues {{
                    id
                    value
                  }}
                }}
              }}
            }}
            """
        }
        response = requests.post(self.endpoint, headers=self.headers, json=query)
        data = response.json()
        return data.get("data", {}).get("product", {}).get("option", {}).get("optionValues", [])

    def link_metafield_to_product_option(
        self, 
        product_id: str, 
        option_id: str, 
        namespace: str = "shopify", 
        key: str = "color-pattern"
    ) -> Dict:
        """
        Links a metafield definition to a specific product option (e.g., 'Color').
        Required before assigning a metaobject to the option value.
        """
        mutation = {
            "query": f"""
            mutation {{
              productOptionUpdate(
                productId: "{product_id}",
                option: {{
                  id: "{option_id}",
                  linkedMetafield: {{
                    namespace: "{namespace}",
                    key: "{key}"
                  }}
                }}
              ) {{
                product {{
                  id
                  title
                  options {{
                    id
                    name
                    linkedMetafield {{
                      namespace
                      key
                    }}
                  }}
                }}
                userErrors {{
                  field
                  message
                }}
              }}
            }}
            """
        }
        response = requests.post(self.endpoint, headers=self.headers, json=mutation)
        return response.json()

    def attach_color_to_variant_option_value(
        self, 
        product_id: str, 
        option_id: str, 
        option_value_id: str, 
        metaobject_gid: str
    ) -> Dict:
        """
        Links a color metaobject to a specific product option value.
        """
        if not metaobject_gid or not metaobject_gid.startswith("gid://shopify/Metaobject/"):
            print(f"!! Invalid metaobject GID: {metaobject_gid}")
            return None

        print(f"[Debug] Attaching color to option value {option_value_id}")
        print(f"[Debug] Color metaobject GID: {metaobject_gid}")
        print(f"[Debug] Formatted value: {json.dumps([metaobject_gid])}")

        # Use inline values in the mutation
        mutation = {
            "query": f"""
            mutation {{
              productOptionUpdate(
                productId: "gid://shopify/Product/{product_id}",
                option: {{
                  id: "{option_id}",
                  linkedMetafield: {{
                    namespace: "shopify",
                    key: "color-pattern"
                  }}
                }},
                optionValuesToUpdate: [
                  {{
                    id: "{option_value_id}",
                    linkedMetafieldValue: "{metaobject_gid}"
                  }}
                ]
              ) {{
                product {{
                  id
                  title
                  options {{
                    name
                    optionValues {{
                      name
                      linkedMetafieldValue
                    }}
                  }}
                }}
                userErrors {{
                  field
                  message
                }}
              }}
            }}
            """
        }

        response = requests.post(self.endpoint, headers=self.headers, json=mutation)
        data = response.json()
        
        if "errors" in data:
            print(f"!! GraphQL errors: {data['errors']}")
            return None
        
        return data

    def get_product_variants(self, product_id: str) -> List[Dict]:
        """Get all variants and their option values for a product"""
        query = {
            "query": f"""
            query {{
              product(id: "{product_id}") {{
                variants(first: 100) {{
                  nodes {{
                    id
                    selectedOptions {{
                      name
                      value
                    }}
                  }}
                }}
              }}
            }}
            """
        }
        response = requests.post(self.endpoint, headers=self.headers, json=query)
        data = response.json()
        return data.get("data", {}).get("product", {}).get("variants", {}).get("nodes", [])

    def create_color_metaobject_if_missing(self, handle: str, label: str, hex_value: str, taxonomy_gid: str, pattern_gid: Optional[str]) -> Optional[str]:
        """
        Check if a metaobject exists by handle. If not, create it.
        Returns the metaobject GID.
        """
        # ✅ First, check if the metaobject already exists
        existing_gid = self.get_metaobject_by_handle(handle)
        if existing_gid:
            print(f"✅ Reusing existing metaobject: {handle}")
            return existing_gid

        SOLID_PATTERN_GID = "gid://shopify/TaxonomyValue/2874"

        # Fallback if pattern_gid is not provided
        if not pattern_gid:
            pattern_gid = SOLID_PATTERN_GID

        if not taxonomy_gid:
            print("🚨 Skipping metaobject creation: Missing color taxonomy GID")
            return None

        print(f"[Debug] Creating metaobject with handle: {handle}")
        print(f"[Debug] Label: {label}, Hex: {hex_value}")
        print(f"[Debug] Color taxonomy: {taxonomy_gid}")
        print(f"[Debug] Pattern taxonomy: {pattern_gid}")

        mutation = {
            "query": f"""
            mutation {{
              metaobjectCreate(metaobject: {{
                type: \"shopify--color-pattern\"
                handle: \"{handle}\"
                fields: [
                  {{ key: \"label\", value: \"{label}\" }},
                  {{ key: \"color\", value: \"{hex_value}\" }},
                  {{ key: \"color_taxonomy_reference\", value: \"[\\\"{taxonomy_gid}\\\"]\" }},
                  {{ key: \"pattern_taxonomy_reference\", value: \"{pattern_gid}\" }}
                ]
              }}) {{
                metaobject {{ id }}
                userErrors {{ field message }}
              }}
            }}
            """
        }
        response = requests.post(self.endpoint, headers=self.headers, json=mutation)
        data = response.json()
        print(f"[Debug] Create metaobject response:\n{json.dumps(data, indent=2)}")

        metaobject = data.get("data", {}).get("metaobjectCreate", {}).get("metaobject")
        if metaobject:
            return metaobject["id"]
        else:
            print("!! Failed to create metaobject - skipping")
            return None

    def assign_palette_to_variant(self, variant_id: str, palette_gids: List[str]) -> Dict:
        """
        Assigns seasonal palettes to the variant via custom.palette metafield.
        Clears any existing palette values before assigning new ones.
        
        Args:
            variant_id: The variant ID to assign palettes to
            palette_gids: List of palette GIDs to assign
        """
        if not palette_gids:
            print(f"!! No palette GIDs provided for variant {variant_id}")
            return None

        # Validate all GIDs
        valid_gids = []
        for gid in palette_gids:
            if gid and gid.startswith("gid://shopify/Metaobject/"):
                valid_gids.append(gid)
            else:
                print(f"!! Invalid palette GID: {gid}")

        if not valid_gids:
            print(f"!! No valid palette GIDs for variant {variant_id}")
            return None

        print(f"[Debug] Assigning palettes to variant {variant_id}")
        print(f"[Debug] Palette GIDs: {json.dumps(valid_gids)}")

        # Set the new palette values (replacing any existing ones)
        metafield_payload = {
            "query": """
            mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
              metafieldsSet(metafields: $metafields) {
                metafields { id key value }
                userErrors { field message }
              }
            }
            """,
            "variables": {
                "metafields": [
                    {
                        "ownerId": variant_id,
                        "namespace": "custom",
                        "key": "palette",
                        "type": "list.metaobject_reference",
                        "value": json.dumps(valid_gids)
                    }
                ]
            }
        }

        response = requests.post(self.endpoint, headers=self.headers, json=metafield_payload)
        return response.json()

    def get_metaobject_by_handle(self, handle: str) -> Optional[str]:
        """
        Look up a metaobject by handle and return its GID if it exists.
        
        Args:
            handle: The handle portion of the metaobject reference (e.g., "pumpkin-b66142")
            
        Returns:
            The metaobject GID if found, None otherwise
        """
        query = """
        query GetMetaobjectByHandle($type: String!, $handle: String!) {
          metaobjectByHandle(handle: { type: $type, handle: $handle }) {
            id
            displayName
            fields {
              key
              value
            }
          }
        }
        """
        
        variables = {
            "type": "shopify--color-pattern",
            "handle": handle
        }
        
        logging.debug(f"Querying metaobject with handle: {handle}")
        logging.debug(f"Full query: {query}")
        logging.debug(f"Variables: {variables}")
        
        response = requests.post(
            self.endpoint,
            headers=self.headers,
            json={
                "query": query,
                "variables": variables
            }
        )
        
        data = response.json()
        logging.debug(f"Response: {data}")
        
        if "errors" in data:
            logging.error(f"GraphQL error: {data['errors']}")
            return None
        
        metaobject = data.get("data", {}).get("metaobjectByHandle")
        if metaobject:
            logging.info(f"Found metaobject: {metaobject['displayName']} ({metaobject['id']})")
            for field in metaobject['fields']:
                logging.debug(f"  {field['key']}: {field['value']}")
            return metaobject['id']
        
        logging.warning(f"No metaobject found with handle: {handle}")
        return None

    def get_product_options(self, product_id: str) -> List[Dict]:
        """Get all options and their values for a product"""
        # Format product ID as Shopify global ID
        product_gid = f"gid://shopify/Product/{product_id}"
        
        query = {
            "query": """
            query GetProductOptions($productId: ID!) {
              product(id: $productId) {
                options {
                  id
                  name
                  optionValues {
                    id
                    name
                    linkedMetafieldValue
                  }
                }
              }
            }
            """,
            "variables": {
                "productId": product_gid
            }
        }

        print(f"[Debug] Fetching options for product {product_gid}")
        response = requests.post(self.endpoint, headers=self.headers, json=query)
        data = response.json()
        
        if "errors" in data:
            print(f"!! GraphQL errors: {data['errors']}")
            return []

        options = data.get("data", {}).get("product", {}).get("options", [])
        
        # Log what we found
        print(f"[Debug] Found {len(options)} options:")
        for opt in options:
            print(f"  - Option: {opt.get('name')} with values:")
            for val in opt.get("optionValues", []):
                print(f"    • {val.get('name')} ({val.get('id')})")

        return options
