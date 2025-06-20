import sys
import csv
from datetime import datetime
from matrixify_utilities.services.shopify_graphql import fetch_products, update_product_metafields

if __name__ == "__main__":
    print("\U0001F680 Starting product attributes update script...")

    mode = sys.argv[1] if len(sys.argv) > 1 else "ALL"
    created_days = int(sys.argv[2]) if len(sys.argv) > 2 else None

    print(f"\U0001F4E6 Mode: {mode}, Created in last N days: {created_days}")

    if mode.upper() == "DRAFT":
        status = "DRAFT"
    elif mode.upper() == "RECENT":
        status = None
    else:
        status = "ACTIVE"

    products = fetch_products(status=status, created_since_days=created_days)

    if not products:
        print("⚠️ No products found with the given filters.")
        sys.exit(0)

    print(f"✅ Found {len(products)} products to process.")

    # Setup CSV logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"product_attributes_log_{timestamp}.csv"
    with open(log_file, mode="w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["product_gid", "title", "status"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for product in products:
            title = product["title"]
            gid = product["id"]
            
            # Define metafields to update
            metafields = [
                {
                    "ownerId": gid,
                    "namespace": "shopify",
                    "key": "target-gender",
                    "type": "list.metaobject_reference",
                    "value": "[\"gid://shopify/Metaobject/215686381940\"]"  # Female
                },
                {
                    "ownerId": gid,
                    "namespace": "shopify",
                    "key": "age-group",
                    "type": "list.metaobject_reference",
                    "value": "[\"gid://shopify/Metaobject/215685857652\"]"  # Adult
                }
            ]

            print(f"🔧 Updating attributes for: {title}")
            result = update_product_metafields(metafields)
            
            if result and not result.get("userErrors"):
                print("✅ Update successful")
                status = "success"
            else:
                print("❌ Update failed:", result.get("userErrors") if result else "Unknown error")
                status = "failed"

            writer.writerow({
                "product_gid": gid,
                "title": title,
                "status": status
            })

    print(f"\n📄 Log written to: {log_file}") 