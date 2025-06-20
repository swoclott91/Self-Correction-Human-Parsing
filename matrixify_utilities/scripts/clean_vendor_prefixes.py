# matrixify_utilities/scripts/clean_vendor_prefixes.py
import sys
import csv
from datetime import datetime
from matrixify_utilities.services.vendor_cleaner import clean_title_and_handle, update_product
from matrixify_utilities.services.shopify_graphql import fetch_products

if __name__ == "__main__":
    print("\U0001F680 Starting vendor prefix cleaner script...")

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
    log_file = f"vendor_prefix_log_{timestamp}.csv"
    with open(log_file, mode="w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["product_gid", "title_before", "title_after", "handle_after"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for product in products:
            title = product["title"]
            gid = product["id"]
            new_title, new_handle = clean_title_and_handle(title)

            if new_title != title:
                print(f"🔧 Updating: {title} → {new_title} ({new_handle})")
                result = update_product(gid, new_title, new_handle)
                print("✅ Update result:", result)

                writer.writerow({
                    "product_gid": gid,
                    "title_before": title,
                    "title_after": new_title,
                    "handle_after": new_handle
                })
            else:
                print(f"⏭️ Skipped (no vendor prefix found): {title}")

    print(f"\n📄 Log written to: {log_file}")