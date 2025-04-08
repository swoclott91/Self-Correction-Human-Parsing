# 🛠️ Setup Guide – Matrixify Utilities (Shopify Product Enrichment)

This document explains how to set up your Python environment for working with the product enrichment pipeline in this repo.

---

## ✅ 1. Create and Activate a Virtual Environment

Open a terminal in the project root and run:

```bash
python -m venv .venv
```

Then activate the environment (Windows):

```bash
.venv\Scripts\activate
```

> ⚠️ Tip: If you're already inside another virtual environment, make sure to deactivate it first using:
> ```bash
> deactivate
> ```

---

## 📦 2. Install Required Dependencies

### Core Shopify + API Requirements

```bash
pip install -r matrixify_utilities/api/requirements.txt
```

### Project-wide Development Requirements

```bash
pip install -r requirements.txt
```

This may include packages like `black`, `rich`, `python-dotenv`, etc.

---

## 🧪 3. Install the Package in Development Mode

This lets you edit source code without reinstalling the package:

```bash
pip install -e .
```

---

## 🚀 4. Run Enrichment Tests

Test the full enrichment pipeline against your 10 most recent Shopify products:

```bash
python -m matrixify_utilities.scripts.test_clothing_update
```

Make sure your `.env` file includes:

```env
SHOPIFY_SHOP_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=your-admin-token
```

---

## 💡 Notes

- You must have access to the Shopify Admin API (2024-04) with read access to products.
- The test script does not make mutations (dry run only).
- Output will be shown using the `rich` library in your terminal.

---

Happy enriching! 🎨🛍️
