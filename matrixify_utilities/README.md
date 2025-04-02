# Color Capsule Matrixify Utilities

Automation tools for enriching Shopify product data with color analysis, metafields, and standardized taxonomy references via Matrixify.

## Project Overview
This toolkit processes Matrixify CSV exports to:
- Normalize size references
- Assign Shopify taxonomy categories
- Extract and analyze garment colors
- Generate color and palette metafields
- Prepare enriched data for reimport

## Setup

### Model Weights
The garment parser requires pre-trained model weights. Download them from:
[exp-schp-201908301523-atr.pth](https://drive.google.com/file/...)

Place the downloaded weights in:
```
matrixify_utilities/models/exp-schp-201908301523-atr.pth
```

## Directory Structure
```
matrixify_utilities/
├── data/               # CSV data at various stages
├── logs/              # Processing logs
├── metaobjects/       # Metaobject generation
├── scripts/           # Main processing scripts
└── tests/             # Test files and data
```

## Workflow Steps
1. Size normalization
2. Category assignment
3. Color extraction
4. Metaobject assignment
5. Palette classification
6. Final CSV generation

## Usage
[Usage instructions to be added] 