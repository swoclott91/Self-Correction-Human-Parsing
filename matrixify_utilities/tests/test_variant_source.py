import sys
import os

# Add the interface directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'interface')))

from variant_source import VariantSource

product_ids = ["14697143894388"]  # Example product

vs = VariantSource()
results = vs.get_variants(product_ids)

for r in results:
    print(r)
