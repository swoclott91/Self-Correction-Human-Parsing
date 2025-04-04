import sys
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import cv2
import numpy as np
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from scripts.normalize_colors import ColorNormalizer
from utils.color_utils import ColorInfo

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def plot_color_swatches(colors: List[ColorInfo], ax, title: str):
    """Display color swatches with frequency information"""
    if not colors:
        ax.text(0.5, 0.5, "No colors detected", ha='center', va='center')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        return
        
    n_colors = len(colors)
    
    # Create color swatches
    for idx, color in enumerate(colors):
        # Create color swatch
        rect = plt.Rectangle(
            (idx/n_colors, 0.2), 1/n_colors, 0.6,
            facecolor=[x/255 for x in color.rgb]
        )
        ax.add_patch(rect)
        
        # Add color information
        ax.text(
            (idx + 0.5)/n_colors, 0.1,
            f'RGB: {color.rgb}\nFreq: {color.frequency:.1f}%',
            ha='center', va='center',
            fontsize=8
        )
    
    ax.set_title(title)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

def test_color_weighting():
    """Test color weighting with visualization"""
    
    # Initialize normalizer
    normalizer = ColorNormalizer()
    
    # Get test file path
    test_file = project_root / 'tests/test_data/sample csv matrixify/products_test_for_re_import.csv'
    
    # Load test data
    df = pd.read_csv(test_file)
    
    # Get first few color variants for testing
    test_variants = df[
        (df['Option1 Name'].str.lower() == 'color') & 
        (df['Variant Image'].notna())
    ][['Option1 Value', 'Variant Image']].drop_duplicates().head(3)
    
    for idx, (_, row) in enumerate(test_variants.iterrows(), 1):
        color_name = row['Option1 Value']
        image_url = row['Variant Image']
        
        logger.info(f"\nProcessing test variant {idx}: {color_name}")
        
        # Download and process image
        local_image_path = normalizer.download_image(image_url)
        if not local_image_path:
            continue
            
        # Create figure for visualization
        fig = plt.figure(figsize=(15, 10))
        gs = plt.GridSpec(3, 2, figure=fig)
        
        # Original image
        ax_img = fig.add_subplot(gs[0, 0])
        img = cv2.imread(local_image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        ax_img.imshow(img)
        ax_img.set_title('Original Image')
        ax_img.axis('off')
        
        # Get mask
        result = normalizer.parser.parse_image(local_image_path)
        mask = normalizer.parser.get_garment_mask(result)
        
        # Show mask
        ax_mask = fig.add_subplot(gs[0, 1])
        ax_mask.imshow(mask, cmap='gray')
        ax_mask.set_title('Garment Mask')
        ax_mask.axis('off')
        
        # Extract colors without weighting
        color_analysis = normalizer.color_extractor.extract_colors(local_image_path, mask)
        original_colors = color_analysis['colors']
        
        # Show original colors
        ax_orig = fig.add_subplot(gs[1, :])
        plot_color_swatches(original_colors, ax_orig, 'Original Color Analysis')
        
        # Apply confidence scoring
        weighted_colors = []
        for color in color_analysis['colors']:
            hsv = normalizer._rgb_to_hsv(color.rgb)
            confidence = normalizer.color_confidence_score(hsv, color_name)
            
            # Adjust color weight based on confidence
            adjusted_frequency = color.frequency * confidence
            weighted_colors.append(ColorInfo(
                rgb=color.rgb,
                lab=color.lab,
                hex=color.hex,
                hsv=hsv,
                frequency=adjusted_frequency
            ))
        
        # Normalize frequencies
        total_freq = sum(c.frequency for c in weighted_colors)
        normalized_colors = [
            ColorInfo(
                rgb=c.rgb,
                lab=c.lab,
                hex=c.hex,
                hsv=c.hsv,
                frequency=(c.frequency/total_freq)*100
            ) for c in weighted_colors
        ]
        
        # Show weighted colors
        ax_weighted = fig.add_subplot(gs[2, :])
        plot_color_swatches(normalized_colors, ax_weighted, 'Weighted Color Analysis')
        
        # Add color name as figure title
        fig.suptitle(f'Color Analysis for {color_name}', fontsize=16)
        
        # Save visualization
        output_dir = project_root / 'data/debug/color_analysis'
        output_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_dir / f'color_analysis_{idx}_{color_name.lower().replace(" ", "_")}.png')
        plt.close()
        
        logger.info(f"Saved visualization to {output_dir}")

if __name__ == '__main__':
    import pandas as pd
    test_color_weighting() 