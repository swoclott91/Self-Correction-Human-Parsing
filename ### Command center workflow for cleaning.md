### Command center workflow for cleaning up and normalizing new products. 

active venv:

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Round prices: 
python -m matrixify_utilities.scripts.round_prices DRAFT

Update Age group to Adults and Target gender to Femal: 
python matrixify_utilities/scripts/update_product_attributes.py DRAFT
python matrixify_utilities/scripts/update_product_attributes.py ALL
python matrixify_utilities/scripts/update_product_attributes.py ALL 7  # Last 7 days

Remove Vendors: 
python -m matrixify_utilities.scripts.clean_vendor_prefixes DRAFT

python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status draft --limit 1500 --batch-size 100 --uncategorized --update --debug
python -m matrixify_utilities.scripts.update_shopify_category_and_attributes --status draft --limit 1500 --batch-size 100 --uncategorized --update

## Always uses draft status

Enrich Colors: 
python -m matrixify_utilities.api_workflows.analyze_and_enrich_colors_api --debug


Script for running agains t a hex code: 

python -m matrixify_utilities.scripts.analyze_hex_color FB8B66