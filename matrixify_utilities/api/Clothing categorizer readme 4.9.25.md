Color Capsule Clothing Categorizer

This repository contains the core logic for auto-categorizing apparel products into the official Shopify taxonomy and enriching them with valid product attributes, using natural language descriptions. It is designed to support bulk enrichment of apparel catalogs sourced from suppliers such as SanMar and enhance data quality for Shopify product listings.

Features

Category Classification: Matches product titles and descriptions to Shopify taxonomy categories (with GID support).

Attribute Extraction: Assigns valid Shopify attributes (e.g., size, fabric, pattern, color) based on recognized patterns.

Confidence Scoring: Calculates normalized confidence scores (0.1 to 2.0) based on keyword quality, position, overlap, etc.

Special Case Logic:

Gives strong preference to products with "set" in the name (e.g., "Top and Shorts Set") to assign the category "Outfit Sets" (gid://shopify/TaxonomyCategory/aa-1-11).

Routes garments with "overalls" to the "One-Pieces" category (gid://shopify/TaxonomyCategory/aa-1-9).

Debug Logging: Outputs detailed logs of keyword matches, attribute processing, and category selection for transparency.

GraphQL-ready Output: Returns valid Shopify category GIDs and metafields for direct import.

Usage

Run the categorizer as part of your product enrichment pipeline. Typical usage

categorizer = ClothingCategorizer(taxonomy, attribute_patterns)
category_gid, confidence = categorizer.categorize(title, description)
attributes = categorizer.extract_attributes(title, description, category_gid)


Output

category_gid: The Shopify TaxonomyCategory GID

confidence: Score from 0.1 (weak match) to 2.0 (very confident)

attributes: A dictionary of attribute GIDs and their matched value GIDs

Key Considerations for Developers

Taxonomy Mapping: Ensure categories.json includes full taxonomy definitions with attribute_info.

Patterns: Extend attribute_patterns.py to expand or refine matching logic per attribute.

Keyword Matching: Controlled in CATEGORY_KEYWORDS. New categories can be added with example keyword lists.

Set Prioritization: Logic for Outfit Sets is in categorize() and gives additional scoring bonuses to any product name that includes "set".

Logging: Uses logging.debug() for detailed tracing. Enable DEBUG level for visibility during development or testing.

Limitations

Color Handling: Currently includes basic pattern matching for Shopify color values, but this logic is being deprecated in favor of a more advanced AI-based workflow. Do not rely on color enrichment in this module for production.

Product Imagery: No support for visual-based classification at this stage. All enrichment is based on textual data.

Context Awareness: The model does not yet account for company, brand, or collection context which may influence classification.

Future Improvements

AI-enhanced Color Assignment: Integration with the Color Capsule's self-correcting human parsing workflow to replace manual color pattern matching with palette-accurate, hex-based color analysis.

Live Shopify Integration: Add writeback support to apply category and attribute updates via the Shopify GraphQL Admin API.

Attribute Weighting Models: Introduce probabilistic logic for attribute certainty and edge cases.

Expanded Training Corpus: Incorporate professionally labeled fashion data for additional patterns, terms, and classifications.

Localization: Add support for multilingual product catalogs.

Maintained by the Color Capsule team. For questions, contributions, or to request support for new attributes or categories, please open an issue or contact us directly.