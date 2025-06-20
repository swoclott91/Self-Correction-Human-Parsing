import sys
from matrixify_utilities.services.price_rounder import round_up_price, update_product_variant_prices
from matrixify_utilities.services.shopify_graphql import fetch_products

if __name__ == "__main__":
    print("🧮 Starting price round-up script...")

    # Get status from command line argument, default to DRAFT if not provided
    status = sys.argv[1] if len(sys.argv) > 1 else "DRAFT"
    
    # Validate status input
    valid_statuses = ["DRAFT", "ACTIVE", "RECENT"]
    if status.upper() not in valid_statuses:
        print(f"❌ Error: Status must be one of {valid_statuses}")
        sys.exit(1)
    
    print(f"📋 Processing {status.upper()} products...")
    products = fetch_products(status=status.upper())
    updated_count = 0

    for product in products:
        print(f"Processing product: {product.get('title', 'Unknown')}")
        variants = product.get("variants", {}).get("edges", [])
        variant_updates = []
        
        for variant_edge in variants:
            variant_node = variant_edge.get("node", {})
            original_price = variant_node.get("price", "0.0")
            variant_id = variant_node.get("id")
            
            if not variant_id:
                print(f"⚠️ Skipping variant - no ID found")
                continue
                
            try:
                rounded_price = round_up_price(original_price)
                
                if rounded_price != original_price:
                    print(f"💲 Updating: {original_price} → {rounded_price}")
                    variant_updates.append({
                        "id": variant_id,
                        "price": rounded_price
                    })
            except Exception as e:
                print(f"❌ Error processing variant: {e}")
                continue
        
        if variant_updates:
            result = update_product_variant_prices(product["id"], variant_updates)
            if result.get("userErrors"):
                print("❌ Update errors:", result["userErrors"])
            else:
                print("✅ Successfully updated variants")
                updated_count += len(variant_updates)

    print(f"\n🏁 Finished. Total variants updated: {updated_count}")
