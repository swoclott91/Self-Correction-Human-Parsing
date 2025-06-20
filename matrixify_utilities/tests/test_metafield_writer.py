# matrixify_utilities/tests/test_metafield_writer.py

from matrixify_utilities.interface.metafield_writer import MetafieldWriter

if __name__ == "__main__":
    print(">> Running metafield writer test")

    # Example product + option identifiers
    product_id = "gid://shopify/Product/14697143894388"
    option_id = "gid://shopify/ProductOption/17023707873652"  # "Color"
    option_value_id = "gid://shopify/ProductOptionValue/7183684010356"  # "LT DENIM"
    color_metaobject_gid = "gid://shopify/Metaobject/216198644084"  # lt-denim-a8b9cb

    # Create writer instance
    writer = MetafieldWriter()

    result = writer.attach_color_to_variant_option_value(
        product_id=product_id,
        option_id=option_id,
        option_value_id=option_value_id,
        metaobject_gid=color_metaobject_gid,
    )

    print(">> Response:")
    print(result)
