import os
from pathlib import Path
import time
import json
from ..interface.variant_source import VariantSource
from ..interface.metafield_writer import MetafieldWriter
from ..utils.garment_parser import GarmentParser
from ..scripts.normalize_colors import ColorNormalizer
from ..utils.palette_classifier import PaletteClassifier, Season
from ..interface.image_fetcher import download_image
from matrixify_utilities.utils.color_utils import Color
from matrixify_utilities.interface.palette_mapper import PALETTE_METAOBJECTS
from typing import List, Dict, Optional

# Constant for solid pattern taxonomy
SOLID_PATTERN_GID = "gid://shopify/TaxonomyValue/2874"

def get_temperature_category(season: Season) -> str:
    """Determine if a season is warm or cool"""
    return {
        Season.SPRING_CLEAR: "warm",
        Season.SPRING_LIGHT: "warm",
        Season.SPRING_WARM: "warm",
        Season.AUTUMN_WARM: "warm",
        Season.AUTUMN_SOFT: "warm",
        Season.AUTUMN_DEEP: "warm",
        Season.SUMMER_COOL: "cool",
        Season.SUMMER_SOFT: "cool",
        Season.SUMMER_LIGHT: "cool",
        Season.WINTER_COOL: "cool",
        Season.WINTER_DEEP: "cool",
        Season.WINTER_CLEAR: "cool"
    }.get(season, "neutral")

def get_tonal_family(season: Season) -> str:
    """Get the tonal family of a season"""
    return {
        Season.SPRING_CLEAR: "clear",
        Season.SPRING_LIGHT: "light",
        Season.SPRING_WARM: "warm",
        Season.AUTUMN_WARM: "warm",
        Season.AUTUMN_SOFT: "soft",
        Season.AUTUMN_DEEP: "deep",
        Season.SUMMER_LIGHT: "light",
        Season.SUMMER_SOFT: "soft",
        Season.SUMMER_COOL: "cool",
        Season.WINTER_DEEP: "deep",
        Season.WINTER_COOL: "cool",
        Season.WINTER_CLEAR: "clear"
    }.get(season, "neutral")

def are_adjacent_tonal_families(season1: Season, season2: Season) -> bool:
    """Check if two seasons are in adjacent tonal families"""
    family1 = get_tonal_family(season1)
    family2 = get_tonal_family(season2)
    
    # Same family is always adjacent
    if family1 == family2:
        return True
        
    # Define adjacency rules
    adjacent_families = {
        "warm": ["soft", "clear"],
        "soft": ["warm", "cool", "light", "deep"],
        "cool": ["soft", "clear"],
        "light": ["soft", "clear"],
        "deep": ["soft", "warm"],
        "clear": ["warm", "cool", "light"]
    }
    
    return family2 in adjacent_families.get(family1, [])

def filter_season_matches(candidate_seasons: List[Season], scores: Dict[Season, float], 
                         max_seasons: int = 2, min_score_threshold: float = 0.90,
                         color_analysis: Optional[Dict] = None) -> List[Season]:
    """Filter season matches based on best practices
    
    Args:
        candidate_seasons: List of candidate seasons to filter
        scores: Dictionary mapping seasons to their scores
        max_seasons: Maximum number of seasons to allow (default 2)
        min_score_threshold: Minimum score threshold relative to top score (default 0.90)
        color_analysis: Optional color analysis results containing chroma values
    """
    if not candidate_seasons:
        return []
        
    # Sort by score
    sorted_seasons = sorted(candidate_seasons, key=lambda s: scores[s], reverse=True)
    
    # Always include the highest scoring season
    final_seasons = [sorted_seasons[0]]
    
    # Get the classifier instance
    classifier = PaletteClassifier()
    
    # Check remaining seasons for compatibility
    for season in sorted_seasons[1:]:
        # Skip if we already have max seasons
        if len(final_seasons) >= max_seasons:
            break
            
        # Skip if score is too low
        if scores[season] < scores[sorted_seasons[0]] * min_score_threshold:
            continue
            
        # Check compatibility with all existing seasons
        is_compatible = True
        for existing_season in final_seasons:
            # Get chroma values from color analysis if available
            if color_analysis and 'chroma' in color_analysis:
                chroma_a = color_analysis['chroma']
                chroma_b = color_analysis['chroma']  # Use same chroma for both since it's the same color
            else:
                # Fallback to default values if no analysis available
                chroma_a = 0.5
                chroma_b = 0.5
            
            if not classifier.should_allow_season_pair(existing_season, season, chroma_a, chroma_b):
                is_compatible = False
                break
        
        if is_compatible:
            final_seasons.append(season)
    
    return final_seasons

def main():
    # Get path to model file
    model_path = str(Path(__file__).parent.parent / 'models' / 'exp-schp-201908301523-atr.pth')
    
    variant_source = VariantSource()
    writer = MetafieldWriter()
    parser = GarmentParser(
        model_path=model_path,  # Use actual model path
        dataset='atr',
        verbose=False
    )
    color_normalizer = ColorNormalizer()
    palette_classifier = PaletteClassifier()

    print(">> Fetching DRAFT status products...")
    products = variant_source.get_draft_product_ids(first=250)

    print(f">> Found {len(products)} draft products to process")
    processed_count = 0
    failed_products = {}  # Track failures by product ID
    skipped_colors = {}   # Track skipped multi-colors
    original_color_names = {}  # Track original color names

    for product_id in products:
        try:
            processed_count += 1
            print(f"\n>> Processing product {processed_count}/{len(products)}: {product_id}")
            
            color_groups = {}
            for variant in variant_source.get_variants([product_id]):
                color = variant["color_option"]
                if not color:
                    print(f"!! Skipping variant - no color option found")
                    continue

                # Handle multi-color names
                original_color = color
                if '/' in color:
                    primary_color = color.split('/')[0].strip()
                    print(f"   - Multi-color detected: {color}, using primary color: {primary_color}")
                    skipped_colors[color] = primary_color
                    color = primary_color
                    original_color_names[color] = original_color  # Store mapping
                    
                if color not in color_groups:
                    color_groups[color] = {
                        "image_url": variant["image_url"],
                        "image_alt": variant["image_alt"],
                        "product_id": product_id,
                        "option_id": variant["color_option_id"],
                        "option_value_id": variant["color_option_value_id"],
                        "variant_ids": [],
                        "original_color": original_color  # Store original name
                    }
                color_groups[color]["variant_ids"].append(variant["variant_id"])

            if not color_groups:
                print("!! No color variants found for this product - skipping")
                continue

            # Process each color group
            for color_label, info in color_groups.items():
                try:
                    print(f">> Processing color: {color_label} on product {product_id}")
                    image_path = download_image(info["image_url"], info["image_alt"])

                    result = parser.parse_image(image_path)
                    mask = parser.get_garment_mask(result)
                    
                    color_analysis = color_normalizer.color_extractor.extract_colors(image_path, mask)
                    if not color_analysis['colors']:
                        print(f"!! No colors extracted for {color_label} - skipping")
                        continue

                    # Use the dominant color (already a ColorInfo object)
                    dominant_color = color_analysis['colors'][0]
                    print(f"   - Detected color: RGB{dominant_color.rgb}, hex: {dominant_color.hex}")

                    # Get season matches using garment classification
                    analysis_result = palette_classifier.classify_garment([dominant_color])
                    season_info = palette_classifier.format_results(analysis_result)

                    primary = season_info["primary_seasons"]
                    secondary = season_info["secondary_seasons"]
                    scores = season_info["scores"]

                    candidate_seasons = primary + secondary

                    if not candidate_seasons:
                        print(f"!! No season matches for {color_label} - skipping")
                        continue

                    # Print matched seasonal candidates
                    print("\nMatched seasonal candidates:")
                    for s in candidate_seasons:
                        print(f"  • {s.value}: {scores[s]:.2%}")

                    # Filter for temperature alignment
                    ref_temp = get_temperature_category(candidate_seasons[0])
                    temp_aligned_seasons = [
                        s for s in candidate_seasons
                        if get_temperature_category(s) == ref_temp
                    ]

                    print(f"Filtered for temperature alignment: {[s.value for s in temp_aligned_seasons]}")

                    # Get color analysis for chroma values
                    color_analysis = palette_classifier._calculate_color_characteristics(dominant_color)
                    color_analysis_dict = {
                        'chroma': color_analysis.chroma,
                        'temperature': color_analysis.temperature,
                        'brightness': color_analysis.brightness,
                        'depth': color_analysis.depth
                    }

                    # Apply best practice filtering
                    final_seasons = filter_season_matches(
                        temp_aligned_seasons, 
                        scores,
                        color_analysis=color_analysis_dict
                    )
                    print(f"Final season selection: {[s.value for s in final_seasons]}")

                    if not final_seasons:
                        print(f"!! No valid season matches for {color_label} - skipping")
                        continue

                    # Get palette GIDs for all matching seasons
                    palette_gids = [
                        PALETTE_METAOBJECTS[s.value] 
                        for s in final_seasons 
                        if s.value in PALETTE_METAOBJECTS
                    ]

                    if not palette_gids:
                        print(f"!! No valid palette GIDs found for seasons - skipping")
                        continue

                    # Map the color to Shopify taxonomy
                    color_taxonomy_gid = color_normalizer.map_to_shopify_color(color_label, dominant_color.hex)
                    print(f"   - Mapped color taxonomy: {color_taxonomy_gid}")

                    # Always use solid pattern for now
                    pattern_taxonomy_gid = SOLID_PATTERN_GID
                    print(f"   - Using pattern taxonomy: {pattern_taxonomy_gid}")

                    if not color_taxonomy_gid:
                        print("!! Missing color taxonomy - skipping")
                        continue

                    handle = f"{color_label.lower().replace(' ', '-')}-{dominant_color.hex.lstrip('#')}"
                    metaobject_gid = writer.create_color_metaobject_if_missing(
                        handle=handle,
                        label=color_label,
                        hex_value=dominant_color.hex,
                        taxonomy_gid=color_taxonomy_gid,
                        pattern_gid=pattern_taxonomy_gid  # Always solid pattern
                    )

                    if not metaobject_gid:
                        print("!! Failed to create metaobject - skipping")
                        continue

                    # After metaobject creation/reuse
                    if metaobject_gid:
                        # Assign to each variant
                        for variant_id in info["variant_ids"]:
                            # Assign all matching palettes at once
                            response = writer.assign_palette_to_variant(variant_id, palette_gids)
                            print(f"[Debug] Assign season palette response:\n{json.dumps(response, indent=2)}")

                        # Get product options and find color option
                        product_options = writer.get_product_options(product_id)
                        if not product_options:
                            print(f"!! No options found for product {product_id}")
                            continue

                        # Try to find color option (case insensitive)
                        color_option = next(
                            (opt for opt in product_options if opt.get("name", "").lower() == "color"), 
                            None
                        )

                        if not color_option:
                            print(f"!! No color option found. Available options: {[opt.get('name') for opt in product_options]}")
                            continue

                        # Find matching option value using original color name
                        option_values = color_option.get("optionValues", [])
                        print(f"[Debug] Looking for color value '{color_label}' (original: '{original_color_names.get(color_label, color_label)}') among {len(option_values)} values:")
                        for val in option_values:
                            print(f"  • {val.get('name')}")

                        # Try to match either simplified or original color name
                        original_color = original_color_names.get(color_label, color_label)
                        value_match = next(
                            (val for val in option_values if val.get("name", "").lower() in [
                                color_label.lower(),
                                original_color.lower()
                            ]),
                            None
                        )

                        if not value_match:
                            print(f"!! No matching color value found for '{color_label}' or '{original_color}'")
                            continue

                        # Attach metaobject to color option value
                        print(f"[Debug] Attaching metaobject to color value '{value_match['name']}'")
                        response = writer.attach_color_to_variant_option_value(
                            product_id=product_id,
                            option_id=color_option["id"],
                            option_value_id=value_match["id"],
                            metaobject_gid=metaobject_gid
                        )
                        print(f"[Debug] Attach color response:\n{json.dumps(response, indent=2)}")
                        print(f"✅ Assigned metaobject to color value {color_label}")

                except Exception as e:
                    error_msg = str(e)
                    failed_products[product_id] = error_msg
                    print(f"!! Error processing color {color_label}: {error_msg}")
                    continue

                # Add delay between colors to respect rate limits
                time.sleep(0.5)

            # Add delay between products to respect rate limits
            time.sleep(1)

        except Exception as e:
            error_msg = str(e)
            failed_products[product_id] = error_msg
            print(f"!! Error processing product {product_id}: {error_msg}")
            continue

    # Print summary report
    print("\n📊 Processing Summary")
    print("-------------------")
    print(f"Total Products: {len(products)}")
    print(f"Successfully Processed: {processed_count - len(failed_products)}")
    print(f"Failed: {len(failed_products)}")

    if failed_products:
        print("\n❌ Failed Products")
        print("----------------")
        for pid, error in failed_products.items():
            print(f"Product {pid}: {error}")

    if skipped_colors:
        print("\n⚠️ Multi-Color Handling")
        print("--------------------")
        print("The following multi-colors were simplified:")
        for original, primary in skipped_colors.items():
            print(f"• {original} → {primary}")

if __name__ == "__main__":
    main()
