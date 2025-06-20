from typing import Optional, Tuple
from ..scripts.normalize_colors import ColorNormalizer
from ..utils.palette_classifier import PaletteClassifier
from ..utils.color_utils import Color

class ColorSeasonMapper:
    def __init__(self):
        self.color_normalizer = ColorNormalizer()
        self.palette_classifier = PaletteClassifier()

    def hex_to_rgb(self, hex_value: str) -> Tuple[int, int, int]:
        """Convert hex to RGB values"""
        hex_value = hex_value.lstrip('#')
        return tuple(int(hex_value[i:i+2], 16) for i in (0, 2, 4))

    def map_hex_to_season(self, hex_value: str) -> Optional[Tuple[str, float, str]]:
        """
        Maps a hex color to its closest seasonal palette.
        
        Args:
            hex_value: The hex color code (e.g., '#A4B19B' or 'A4B19B')
            
        Returns:
            Tuple of (season_name, confidence, explanation) or None if no match
        """
        # Ensure hex value is properly formatted
        hex_value = hex_value.strip('#')
        if len(hex_value) != 6:
            print(f"!! Invalid hex value: {hex_value}")
            return None

        try:
            # Create Color object with hex string
            color = Color(f"#{hex_value}")
        except ValueError as e:
            print(f"!! Invalid hex value: {hex_value}")
            return None

        # Get season matches
        season_matches = self.palette_classifier.classify_color(color)
        if not season_matches:
            print(f"!! No season matches for {hex_value}")
            return None

        # Use the highest confidence match
        best_match = season_matches[0]
        
        return (
            best_match.season.value,
            best_match.confidence,
            best_match.explanation
        )

    def analyze_color(self, hex_value: str) -> dict:
        """
        Provides a complete analysis of a hex color including season and color taxonomy.
        
        Args:
            hex_value: The hex color code
            
        Returns:
            Dictionary containing analysis results
        """
        season_info = self.map_hex_to_season(hex_value)
        if not season_info:
            return {"success": False, "error": "Could not determine season"}

        season, confidence, explanation = season_info
        
        # Get color taxonomy mapping
        taxonomy_gid = self.color_normalizer.map_to_shopify_color("Color", f"#{hex_value}")

        return {
            "success": True,
            "hex_value": f"#{hex_value}",
            "season": {
                "name": season,
                "confidence": confidence,
                "explanation": explanation
            },
            "taxonomy": {
                "gid": taxonomy_gid
            }
        } 