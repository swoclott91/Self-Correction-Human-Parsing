Category Readme

# Matrixify Utilities

Utilities for managing Shopify product data with Matrixify, including taxonomy mapping, category management, and product enrichment.

## Setup

### 1. Environment Setup

First, create and activate a Python virtual environment:
bash
Create virtual environment
python -m venv venv
Activate virtual environment
On Windows:
venv\Scripts\activate
On macOS/Linux:
source venv/bin/activate



### 2. Installation

Install the package in development mode:
bash
Install package and dependencies
pip install -e .
Install additional development dependencies
pip install -r requirements.txt


### 3. Configuration

Create a `.env` file in the root directory with your Shopify credentials:
env
Shopify Store URL (your-store.myshopify.com)
SHOPIFY_SHOP_URL=your-store.myshopify.com
Shopify Admin API Access Token
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxx



## Available Commands

After installation, the following commands are available:

- `test-clothing`: Test clothing categorization
- `search-categories`: Search available Shopify categories
- `explore-mappings`: Explore taxonomy mappings
- `manage-categories`: Manage product categories
- `test-colors`: Test color normalization
- `print-taxonomy`: Print taxonomy structure

Example usage:

bash
Test clothing categorization
test-clothing
Print taxonomy structure
print-taxonomy


## Project Structure
matrixify_utilities/
├── api/
│ ├── client.py # Shopify API client
│ └── requirements.txt # API-specific requirements
├── scripts/
│ ├── test_clothing_update.py
│ ├── search_categories.py
│ └── ...
└── taxonomy_data/
├── categories.json
├── attributes.json
└── values.json


## Development

### Running Tests

bash
pytest


### Code Formatting
bash
Format code
black .
Check style
flake8


## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure virtual environment is activated
   - Verify package is installed in dev mode (`pip install -e .`)

2. **API Connection Issues**
   - Check `.env` file exists and contains valid credentials
   - Verify Shopify API access token has required scopes

3. **Missing Dependencies**
   - Run `pip install -r requirements.txt`
   - Check Python version (requires >=3.8)

### Getting Help

If you encounter issues:
1. Check the logs (default location: `./logs`)
2. Verify environment setup
3. Ensure all dependencies are installed

## License

[Your License Here]


# Matrixify Utilities for Shopify

Utilities for managing Shopify product data with Matrixify, including taxonomy mapping, category management, and product enrichment.

## Quick Start

### 1. Create Virtual Environment

```bash
# Create a new virtual environment
python -m venv .venv

# Activate the environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install core dependencies
pip install -r matrixify_utilities/api/requirements.txt

# Install development dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### 3. Configure Shopify Access

Create a `.env` file in the root directory:

```env
# Shopify Store URL (your-store.myshopify.com)
SHOPIFY_SHOP_URL=your-store.myshopify.com

# Shopify Admin API Access Token
# Generate from Shopify Admin > Apps > Develop apps
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Usage

### Test Clothing Categorization

```bash
# Test the categorization pipeline
python -m matrixify_utilities.scripts.test_clothing_update
```

### Available Commands

After installation, these CLI commands become available:

```bash
# Test clothing categorization
test-clothing

# Search available categories
search-categories

# Explore taxonomy mappings
explore-mappings

# Manage product categories
manage-categories

# Test color normalization
test-colors

# Print taxonomy structure
print-taxonomy
```

## Project Structure

```
matrixify_utilities/
├── api/                    # API clients and core functionality
│   ├── client.py          # Shopify API client
│   └── requirements.txt   # Core dependencies
├── scripts/               # Command-line tools
│   ├── test_clothing_update.py
│   └── ...
└── taxonomy_data/         # Taxonomy mapping data
    ├── categories.json
    ├── attributes.json
    └── values.json
```

## Troubleshooting

### Common Installation Issues

1. **Missing Dependencies**
   ```bash
   # If you see ModuleNotFoundError, try reinstalling requirements:
   pip install -r matrixify_utilities/api/requirements.txt --force-reinstall
   ```

2. **Import Errors**
   ```bash
   # Ensure you're in the right directory and virtual environment is activated
   # Your prompt should show (.venv)
   ```

3. **API Connection Issues**
   - Verify your `.env` file exists and contains valid credentials
   - Check Shopify Admin API access token has required scopes:
     - `read_products`
     - `write_products`

### Getting Help

If you encounter issues:
1. Check the logs (default location: `./logs`)
2. Verify your Python version matches requirements (>=3.8)
3. Ensure all dependencies are installed correctly
4. Check your Shopify API credentials

## Development

### Code Style

```bash
# Format code
black .

# Check style
flake8
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest matrixify_utilities/tests/test_categorizer.py
```

## License

MIT License - See LICENSE file for details