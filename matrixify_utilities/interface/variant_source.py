import requests
import os
from typing import List, Dict, Literal
from dotenv import load_dotenv

# Load environment variables
load_dotenv("C:/Users/Shane Work/Documents/GitHub/Self-Correction-Human-Parsing/.env")
SHOPIFY_SHOP_URL = os.getenv("SHOPIFY_SHOP_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

SHOPIFY_API_URL = f"https://{SHOPIFY_SHOP_URL}/admin/api/2025-04/graphql.json"


class VariantSource:
    """
    Interface class to unify variant data input from either Matrixify CSV or Shopify API.
    This version fetches product variant data from the Shopify Admin API.
    Place this file in: matrixify_utilities/interface/variant_source.py
    """

    def __init__(self, source: Literal["api", "csv"] = "api"):
        self.source = source
        self.endpoint = SHOPIFY_API_URL
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        }

    def get_variants(self, product_ids: List[str]) -> List[Dict]:
        """
        For each product ID, fetch variants with image, selectedOptions (color/size), category, and variant ID.
        """
        all_variants = []
        for product_id in product_ids:
            color_option_id = self.get_color_option_id(product_id)
            color_value_map = self.get_color_option_value_ids(product_id)

            query = {
                "query": f"""
                query {{
                  product(id: \"gid://shopify/Product/{product_id}\") {{
                    id
                    title
                    productCategory {{
                      productTaxonomyNode {{
                        id
                        fullName
                      }}
                    }}
                    variants(first: 100) {{
                      nodes {{
                        id
                        title
                        image {{
                          originalSrc
                          altText
                        }}
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
            if errors := data.get("errors"):
                print("GraphQL Error:", errors)
                continue

            product = data["data"]["product"]
            category_info = product.get("productCategory", {}).get("productTaxonomyNode", {})
            category_id = category_info.get("id")
            category_full_name = category_info.get("fullName")

            for variant in product["variants"]["nodes"]:
                variant_data = {
                    "product_title": product["title"],
                    "variant_id": variant["id"],
                    "variant_title": variant["title"],
                    "image_url": variant["image"]["originalSrc"] if variant["image"] else None,
                    "image_alt": variant["image"]["altText"] if variant["image"] else None,
                    "color_option": None,
                    "size_option": None,
                    "color_option_id": color_option_id,
                    "color_option_value_id": None,
                    "category_id": category_id,
                    "category_name": category_full_name,
                }
                for opt in variant["selectedOptions"]:
                    if opt["name"].lower() == "color":
                        variant_data["color_option"] = opt["value"]
                        variant_data["color_option_value_id"] = color_value_map.get(opt["value"])
                    elif opt["name"].lower() == "size":
                        variant_data["size_option"] = opt["value"]
                all_variants.append(variant_data)

        return all_variants

    def get_draft_product_ids(self, first: int = 50) -> List[str]:
        """
        Fetches a list of product IDs that are currently in DRAFT status.
        Useful as a starting point for workflows that operate on new or unpublished products.
        """
        query = {
            "query": f"""
            query {{
              products(first: {first}, query: \"status:draft\") {{
                edges {{
                  node {{
                    id
                    title
                  }}
                }}
              }}
            }}
            """
        }
        response = requests.post(self.endpoint, headers=self.headers, json=query)
        data = response.json()
        if errors := data.get("errors"):
            print("GraphQL Error:", errors)
            return []

        return [edge["node"]["id"].split("/")[-1] for edge in data["data"]["products"]["edges"]]

    def get_color_option_id(self, product_id: str) -> str:
        """
        Returns the product option ID for the 'Color' option.
        """
        query = {
            "query": f"""
            query {{
              product(id: \"gid://shopify/Product/{product_id}\") {{
                options {{
                  id
                  name
                }}
              }}
            }}
            """
        }
        response = requests.post(self.endpoint, headers=self.headers, json=query)
        data = response.json()
        options = data["data"]["product"]["options"]
        for option in options:
            if option["name"].lower() == "color":
                return option["id"]
        return None

    def get_color_option_value_ids(self, product_id: str) -> Dict[str, str]:
        """
        Returns mapping of color option value (e.g. 'Black') to its optionValue GID.
        """
        query = {
            "query": f"""
            query {{
              product(id: \"gid://shopify/Product/{product_id}\") {{
                options {{
                  id
                  name
                  values
                  optionValues {{
                    id
                    name
                  }}
                }}
              }}
            }}
            """
        }
        response = requests.post(self.endpoint, headers=self.headers, json=query)
        data = response.json()
        if errors := data.get("errors"):
            print("GraphQL Error:", errors)
            return {}

        options = data["data"]["product"]["options"]
        color_mapping = {}
        for opt in options:
            if opt["name"].lower() == "color":
                for value in opt["optionValues"]:
                    color_mapping[value["name"]] = value["id"]
        return color_mapping

    def get_color_option_ids(self, product_id: str, color_value: str) -> Dict[str, str]:
        """
        Get the option ID and option value ID for a specific color value.
        
        Args:
            product_id: Shopify product GID
            color_value: The color value to look up (e.g., "Black")
            
        Returns:
            Dict with color_option_id and color_option_value_id
        """
        query = {
            "query": """
            query getColorOptions($productId: ID!) {
              product(id: $productId) {
                options {
                  id
                  name
                  optionValues {
                    id
                    name
                  }
                }
              }
            }
            """,
            "variables": {
                "productId": product_id
            }
        }
        
        response = requests.post(self.endpoint, headers=self.headers, json=query)
        data = response.json()
        
        options = data.get("data", {}).get("product", {}).get("options", [])
        color_option = next((opt for opt in options if opt["name"].lower() == "color"), None)
        
        if not color_option:
            raise ValueError(f"No color option found for product {product_id}")
        
        color_value_id = next(
            (val["id"] for val in color_option["optionValues"] if val["name"] == color_value),
            None
        )
        
        if not color_value_id:
            raise ValueError(f"Color value '{color_value}' not found in product {product_id}")
        
        return {
            "color_option_id": color_option["id"],
            "color_option_value_id": color_value_id
        }
