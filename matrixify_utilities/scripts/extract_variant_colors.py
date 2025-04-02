import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from utils.color_utils import ColorExtractor, ColorInfo
from utils.garment_parser import GarmentParser
from utils.palette_classifier import PaletteClassifier
import numpy as np
import pandas as pd
import requests
from urllib.parse import urlparse
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import cv2
from datetime import datetime

def get_color_and_season(image_path, category_path=None):
    """Get primary color (hex) and season matches for a garment image.
    
    Args:
        image_path: Path to image file
        category_path: Shopify taxonomy path (e.g. "Apparel & Accessories > Clothing > One-Pieces")
    """
    # Suppress all logging
    logging.getLogger().setLevel(logging.WARNING)
    
    # Initialize components silently
    parser = GarmentParser(
        model_path='models/exp-schp-201908301523-atr.pth',
        dataset='atr',
        verbose=False
    )
    color_extractor = ColorExtractor(
        n_colors=5, 
        lab_threshold=30,
        verbose=False
    )
    classifier = PaletteClassifier(use_rules=True)
    
    # Get mask based on category
    result = parser.parse_image(image_path)
    mask = parser.get_garment_mask(
        result,
        category_path=category_path
    )
    
    # Extract colors using the mask
    color_analysis = color_extractor.extract_colors(image_path, mask)
    
    # Check if we got any colors
    if not color_analysis['colors']:
        return None, []
        
    # Get primary color hex
    primary_color = color_analysis['colors'][0]
    hex_color = primary_color.hex
    
    # Get season matches
    garment_analysis = classifier.classify_garment(
        color_analysis['colors'],
        primary_threshold=0.98,
        secondary_threshold=0.90,
        min_confidence=0.6,
        pattern_threshold=0.02
    )
    results = classifier.format_results(garment_analysis)
    
    # Get primary seasons
    primary_seasons = [
        season.value 
        for season in results['primary_seasons']
    ]
    
    return hex_color, primary_seasons

def download_image(url, save_dir='data/temp_images'):
    """Download image from URL and save locally"""
    os.makedirs(save_dir, exist_ok=True)
    
    # Get filename from URL and make unique
    url_hash = str(hash(url))[-8:]  # Use last 8 digits of hash
    filename = f"{url_hash}_{os.path.basename(urlparse(url).path.split('?')[0])}"
    save_path = os.path.join(save_dir, filename)
    
    # Download if doesn't exist
    if not os.path.exists(save_path):
        try:
            response = requests.get(url)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded {filename}")
        except Exception as e:
            print(f"Error downloading {url}: {str(e)}")
            return None
            
    return save_path

def visualize_segmentation(image_path, result, mask, color_analysis, category, save_dir='debug_visualizations'):
    """Create debug visualization of segmentation and color analysis"""
    try:
        os.makedirs(save_dir, exist_ok=True)
        
        # Create unique filename using timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = os.path.basename(image_path).split('?')[0]
        save_name = f"{timestamp}_{base_name}_debug.png"
        save_path = os.path.join(save_dir, save_name)
        
        # Create figure with grid
        fig = plt.figure(figsize=(15, 10))
        gs = GridSpec(2, 3, figure=fig)
        
        # Original image
        ax1 = fig.add_subplot(gs[0, 0])
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Could not read image {image_path}")
            return
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        ax1.imshow(img)
        ax1.set_title('Original Image')
        ax1.axis('off')
        
        # Segmentation mask
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.imshow(mask, cmap='gray')
        ax2.set_title(f'Segmentation Mask\n{category}')
        ax2.axis('off')
        
        # Masked image
        ax3 = fig.add_subplot(gs[0, 2])
        masked_img = img.copy()
        masked_img[mask == 0] = [0, 0, 0]
        ax3.imshow(masked_img)
        ax3.set_title('Masked Image')
        ax3.axis('off')
        
        # Color swatches
        ax4 = fig.add_subplot(gs[1, :])
        ax4.set_xlim(0, 1)
        ax4.set_ylim(0, 1)
        ax4.axis('off')
        
        # Display color information
        color_info = ""
        x = 0.1
        for color in color_analysis['colors']:
            # Fix hex color format (remove extra #)
            hex_color = color.hex.replace('##', '#')
            
            # Create color swatch
            rect = plt.Rectangle((x, 0.2), 0.1, 0.6, 
                               facecolor=hex_color, 
                               edgecolor='black')
            ax4.add_patch(rect)
            
            # Add color info text
            color_info += f"RGB{color.rgb} ({color.frequency:.1f}%)\nHex: {hex_color}\n\n"
            x += 0.2
        
        ax4.text(0.1, 0.9, color_info, transform=ax4.transAxes, verticalalignment='top')
        
        # Save figure
        plt.savefig(save_path, bbox_inches='tight', dpi=300)
        plt.close()
        
        print(f"Saved visualization to {save_path}")
        
    except Exception as e:
        print(f"Error creating visualization: {str(e)}")
        import traceback
        traceback.print_exc()

def process_shopify_csv(csv_path):
    """Process Shopify CSV export with image URLs
    
    Expected columns:
    - Column Q: Image URLs
    - Column H: Category names
    """
    # Create results directory
    results_dir = 'analysis_results'
    os.makedirs(results_dir, exist_ok=True)
    
    # Initialize components
    parser = GarmentParser(
        model_path='models/exp-schp-201908301523-atr.pth',
        dataset='atr',
        verbose=False
    )
    color_extractor = ColorExtractor(
        n_colors=5,
        lab_threshold=30,
        verbose=False
    )
    classifier = PaletteClassifier(use_rules=True)
    
    # Read CSV
    df = pd.read_csv(csv_path)
    
    # Process each row
    results = []
    
    for idx, row in df.iterrows():
        image_url = row.iloc[16]  # Column Q
        category = row.iloc[7]    # Column H
        
        if pd.isna(image_url) or pd.isna(category):
            print(f"Skipping row {idx+1}: Missing image URL or category")
            continue
            
        try:
            # Download image
            image_path = download_image(image_url)
            if image_path is None:
                print(f"Skipping row {idx+1}: Failed to download image")
                continue
                
            # Verify image can be read
            img = cv2.imread(image_path)
            if img is None:
                print(f"Skipping row {idx+1}: Cannot read image file")
                continue
            
            # Map category to full taxonomy path
            category_path = f"Apparel & Accessories > Clothing > {category}"
            
            # Get parsing result and mask
            result = parser.parse_image(image_path)
            mask = parser.get_garment_mask(result, category_path=category_path)
            
            # Extract colors
            color_analysis = color_extractor.extract_colors(image_path, mask)
            
            if not color_analysis['colors']:
                print(f"Warning: No colors extracted for row {idx+1}")
                continue
                
            # Get color and season analysis
            primary_color = color_analysis['colors'][0]
            hex_color = primary_color.hex.replace('##', '#')  # Fix double #
            
            # Get detailed season analysis
            garment_analysis = classifier.classify_garment(
                color_analysis['colors'],
                primary_threshold=0.98,
                secondary_threshold=0.90,
                min_confidence=0.6,
                pattern_threshold=0.02
            )
            season_results = classifier.format_results(garment_analysis)
            
            # Create debug visualization
            visualize_segmentation(image_path, result, mask, color_analysis, category)
            
            # Store results
            results.append({
                'image_url': image_url,
                'category': category_path,
                'hex_color': hex_color,
                'primary_seasons': [s.value for s in season_results['primary_seasons']],
                'secondary_seasons': [s.value for s in season_results['secondary_seasons']],
                'color_characteristics': [m.explanation for m in classifier.classify_color(primary_color)]
            })
            
            # Print analysis
            print(f"\nProcessed {idx+1}: {category}")
            print(f"Color: {hex_color}")
            print("\nPrimary Seasons:")
            for season in season_results['primary_seasons']:
                score = season_results['scores'][season] * 100
                print(f"  {season.value}: {score:.1f}%")
            
            if season_results['secondary_seasons']:
                print("\nSecondary Seasons:")
                for season in season_results['secondary_seasons']:
                    score = season_results['scores'][season] * 100
                    print(f"  {season.value}: {score:.1f}%")
            
            print("\nColor Characteristics:")
            for color in color_analysis['colors']:
                matches = classifier.classify_color(color)
                if matches:
                    print(f"  {matches[0].explanation}")
            
        except Exception as e:
            print(f"Error processing row {idx+1}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Save results to new directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join(results_dir, f'color_analysis_{timestamp}.csv')
    
    try:
        results_df = pd.DataFrame(results)
        results_df.to_csv(output_path, index=False)
        print(f"\nResults saved to {output_path}")
    except Exception as e:
        print(f"Error saving results: {str(e)}")
        # Try alternative location
        alt_path = os.path.join('debug_visualizations', f'color_analysis_{timestamp}.csv')
        try:
            results_df.to_csv(alt_path, index=False)
            print(f"Results saved to alternative location: {alt_path}")
        except Exception as e2:
            print(f"Could not save results to alternative location: {str(e2)}")
    
    return results_df

# Make sure this is available for import
__all__ = ['process_shopify_csv']

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python get_color_season.py <csv_file_or_image_path>")
        sys.exit(1)
        
    path = sys.argv[1]
    csv_path = r"C:\Users\Shane Work\Documents\GitHub\Self-Correction-Human-Parsing\data\sample csv matrixify\products and variants.csv"
    
    if path.lower().endswith('.csv'):
        # Process Shopify CSV
        results = process_shopify_csv(path)
        print("\nResults saved to", os.path.splitext(path)[0] + '_color_results.csv')
    else:
        # Original single image processing code...
        if os.path.isdir(path):
            # Process directory
            image_files = [f for f in os.listdir(path) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
            for image_file in image_files:
                image_path = os.path.join(path, image_file)
                hex_color, seasons = get_color_and_season(image_path)
                if hex_color:
                    print(f"\n{image_file}:")
                    print(f"Color: {hex_color}")
                    print("Primary Seasons:", ", ".join(seasons))
                else:
                    print(f"\nWarning: Could not extract colors from {image_file}")
        else:
            # Process single image
            hex_color, seasons = get_color_and_season(path)
            if hex_color:
                print(f"Color: {hex_color}")
                print("Primary Seasons:", ", ".join(seasons))
            else:
                print("Warning: Could not extract colors from image") 