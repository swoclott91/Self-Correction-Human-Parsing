import sys
from ..services.color_season_mapper import ColorSeasonMapper
from ..interface.palette_mapper import PALETTE_METAOBJECTS

def main():
    try:
        # Check if hex code was provided
        if len(sys.argv) < 2:
            print("Usage: python -m matrixify_utilities.scripts.analyze_hex_color <hex_code>")
            print("Example: python -m matrixify_utilities.scripts.analyze_hex_color 435499")
            sys.exit(1)

        # Get hex code from command line
        hex_code = sys.argv[1].strip('#')  # Remove # if present
        
        # Initialize mapper
        mapper = ColorSeasonMapper()
        
        # Analyze the color
        print(f"\nAnalyzing hex color: #{hex_code}")
        result = mapper.analyze_color(hex_code)
        
        if result["success"]:
            season_info = result["season"]
            season_gid = PALETTE_METAOBJECTS.get(season_info["name"])
            
            print("\n🎨 Color Analysis Results")
            print("------------------------")
            print(f"Hex Value: #{hex_code}")
            print(f"Season: {season_info['name']} ({season_info['confidence']:.1f}%)")
            print(f"Explanation: {season_info['explanation']}")
            print("\n📍 Shopify References")
            print("------------------------")
            print(f"Color Taxonomy: {result['taxonomy']['gid']}")
            print(f"Season Palette: {season_gid}")
        else:
            print(f"❌ Error: {result['error']}")

    except Exception as e:
        print(f"❌ Error analyzing color: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 