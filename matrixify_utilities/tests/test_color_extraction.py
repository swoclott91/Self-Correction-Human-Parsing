from utils.color_utils import ColorExtractor
from simple_extractor import GarmentParser
import matplotlib.pyplot as plt
import numpy as np
import os
import cv2

def display_colors(colors, ax, title=None):
    """Display color swatches with information"""
    if not colors:
        ax.text(0.5, 0.5, "No colors detected", ha='center', va='center')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        return
        
    n_colors = len(colors)
    
    # Create main color swatches
    for idx, color in enumerate(colors):
        # Create color swatch
        rect = plt.Rectangle(
            (idx/n_colors, 0.2), 1/n_colors, 0.6,
            facecolor=[x/255 for x in color.rgb]
        )
        ax.add_patch(rect)
        
        # Add pattern indicator bar if part of a pattern
        if getattr(color, 'is_pattern', False):
            pattern_rect = plt.Rectangle(
                (idx/n_colors, 0), 1/n_colors, 0.1,
                facecolor='gold',
                alpha=0.8
            )
            ax.add_patch(pattern_rect)
            pattern_status = "Pattern"
        else:
            pattern_status = "Solid"
        
        # Add detailed color information
        hsv = color.hsv
        ax.text(
            (idx + 0.5)/n_colors, 0.5,
            f'{pattern_status}\n'
            f'RGB: {color.rgb}\n'
            f'HSV: ({int(hsv[0])}°, {int(hsv[1])}%, {int(hsv[2])})\n'
            f'Freq: {color.frequency:.1f}%',
            ha='center', va='center',
            rotation=0,
            color='white' if sum(color.rgb) < 380 else 'black',
            fontsize=8
        )
    
    if title:
        ax.set_title(title)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

def print_color_analysis(colors):
    """Print detailed color analysis"""
    print("\nDetailed Color Analysis:")
    print("-" * 50)
    
    # Group colors by type
    primary_colors = []
    pattern_colors = []
    secondary_colors = []
    
    for color in colors:
        if color.frequency >= 5.0:
            if getattr(color, 'is_pattern', False):
                pattern_colors.append(color)
            else:
                primary_colors.append(color)
        else:
            secondary_colors.append(color)
    
    # Print primary colors
    print("\nPrimary Colors (>5%):")
    for color in primary_colors:
        hsv = color.hsv
        print(f"- RGB{color.rgb} ({color.frequency:.1f}%)")
        print(f"  HSV: {int(hsv[0])}° hue, {int(hsv[1])}% saturation, {int(hsv[2])} value")
    
    # Print pattern colors
    if pattern_colors:
        print("\nPattern Colors:")
        for color in pattern_colors:
            hsv = color.hsv
            print(f"- RGB{color.rgb} ({color.frequency:.1f}%)")
            print(f"  HSV: {int(hsv[0])}° hue, {int(hsv[1])}% saturation, {int(hsv[2])} value")
    
    # Print secondary colors
    if secondary_colors:
        print("\nSecondary Colors (<5%):")
        for color in secondary_colors:
            print(f"- RGB{color.rgb} ({color.frequency:.1f}%)")

def visualize_mask_overlay(img, mask, ax, title=None):
    """Visualize mask overlay on image"""
    # Ensure mask and image have same dimensions
    if mask.shape[:2] != img.shape[:2]:
        mask = cv2.resize(mask.astype(np.float32), 
                         (img.shape[1], img.shape[0]),
                         interpolation=cv2.INTER_NEAREST)
    
    # Create overlay
    overlay = img.copy()
    overlay[mask == 0] = [0, 0, 0]
    
    # Create a blended visualization
    alpha = 0.7
    blended = cv2.addWeighted(img, 1-alpha, overlay, alpha, 0)
    
    ax.imshow(blended)
    if title:
        ax.set_title(title)
    ax.axis('off')

def debug_mask_alignment(img, mask):
    """Debug mask alignment issues"""
    print("\nMask Alignment Debug:")
    print(f"Image shape: {img.shape}")
    print(f"Mask shape: {mask.shape}")
    
    # Check if dimensions match
    if img.shape[:2] != mask.shape[:2]:
        print("WARNING: Mask and image dimensions don't match!")
        print(f"Image (H,W): {img.shape[:2]}")
        print(f"Mask (H,W): {mask.shape[:2]}")
    
    # Add to test_extraction():
    img = plt.imread(image_path)
    debug_mask_alignment(img, mask_steps['final_mask'])

def debug_transform_visualization(img, mask, ax_original, ax_mask, ax_overlay):
    """Visualize the transformation alignment"""
    # Original image with dimensions
    ax_original.imshow(img)
    ax_original.set_title(f'Original Image {img.shape[:2]}')
    
    # Mask with dimensions
    ax_mask.imshow(mask, cmap='gray')
    ax_mask.set_title(f'Mask {mask.shape[:2]}')
    
    # Overlay with grid
    if mask.shape[:2] != img.shape[:2]:
        mask = cv2.resize(mask.astype(np.float32), 
                         (img.shape[1], img.shape[0]),
                         interpolation=cv2.INTER_NEAREST)
    
    # Create grid
    grid_size = 50
    grid_img = img.copy()
    h, w = img.shape[:2]
    
    # Draw vertical lines
    for x in range(0, w, grid_size):
        cv2.line(grid_img, (x, 0), (x, h), (255, 0, 0), 1)
    
    # Draw horizontal lines
    for y in range(0, h, grid_size):
        cv2.line(grid_img, (0, y), (w, y), (255, 0, 0), 1)
    
    # Create overlay with grid
    overlay = grid_img.copy()
    overlay[mask == 0] = [0, 0, 0]
    alpha = 0.7
    blended = cv2.addWeighted(grid_img, 1-alpha, overlay, alpha, 0)
    
    ax_overlay.imshow(blended)
    ax_overlay.set_title('Overlay with Grid')

def test_extraction():
    # Initialize extractors
    parser = GarmentParser(
        model_path='models/exp-schp-201908301523-atr.pth',
        dataset='atr'
    )
    color_extractor = ColorExtractor(
        n_colors=5, 
        lab_threshold=15,
        min_pattern_area=0.02
    )
    
    # Process images
    test_dir = 'data/test_img'
    image_files = [f for f in os.listdir(test_dir) 
                  if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    
    for image_file in image_files:
        print(f"\n{'='*20} Processing {image_file} {'='*20}")
        image_path = os.path.join(test_dir, image_file)
        
        # Get initial parsing result
        result = parser.parse_image(image_path)
        
        # Get mask refinement steps
        mask_steps = parser.get_garment_mask_steps(result, garment_type='upper')
        
        # Extract colors with background color information
        color_analysis = color_extractor.extract_colors(
            image_path, 
            mask_steps['final_mask'],
            background_color=mask_steps.get('background_color')
        )
        
        # Print detailed analysis
        print_color_analysis(color_analysis['colors'])
        
        # Visualization
        fig = plt.figure(figsize=(15, 15))
        gs = fig.add_gridspec(6, 2, height_ratios=[3, 3, 3, 2, 2, 2])
        
        # Original image
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.imshow(plt.imread(image_path))
        ax1.set_title('Original Image')
        ax1.axis('off')
        
        # Initial mask
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.imshow(mask_steps['initial_mask'], cmap='gray')
        ax2.set_title('Initial Garment Mask')
        ax2.axis('off')
        
        # Excluded regions
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.imshow(mask_steps['exclude_mask'], cmap='gray')
        ax3.set_title('Excluded Regions')
        ax3.axis('off')
        
        # After exclusion
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.imshow(mask_steps['after_exclusion'], cmap='gray')
        ax4.set_title('After Region Exclusion')
        ax4.axis('off')
        
        # Final refined mask
        ax5 = fig.add_subplot(gs[2, 0])
        ax5.imshow(mask_steps['final_mask'], cmap='gray')
        ax5.set_title('Final Refined Mask')
        ax5.axis('off')
        
        # Original image with mask overlay
        ax6 = fig.add_subplot(gs[2, 1])
        visualize_mask_overlay(plt.imread(image_path), 
                             mask_steps['final_mask'],
                             ax6,
                             'Mask Overlay')
        
        # Color analysis
        ax7 = fig.add_subplot(gs[3, :])
        display_colors(color_analysis['colors'], ax7, 'All Detected Colors')
        ax7.axis('off')
        
        # Primary colors
        primary_colors = [c for c in color_analysis['colors'] if c.frequency >= 5.0]
        ax8 = fig.add_subplot(gs[4, :])
        display_colors(primary_colors, ax8, 'Primary Colors (>5%)')
        ax8.axis('off')
        
        # Secondary colors
        secondary_colors = [c for c in color_analysis['colors'] 
                          if c.frequency < 5.0 and c.frequency >= 2.0]
        ax9 = fig.add_subplot(gs[5, :])
        display_colors(secondary_colors, ax9, 'Secondary Colors (2-5%)')
        ax9.axis('off')
        
        # Add debug visualization
        fig_debug = plt.figure(figsize=(15, 5))
        ax_orig = fig_debug.add_subplot(131)
        ax_mask = fig_debug.add_subplot(132)
        ax_overlay = fig_debug.add_subplot(133)
        
        img = plt.imread(image_path)
        debug_transform_visualization(img, mask_steps['final_mask'], 
                                   ax_orig, ax_mask, ax_overlay)
        plt.suptitle('Alignment Debug')
        plt.show()

        plt.suptitle(f'Color Analysis: {image_file}', y=0.95)
        plt.tight_layout()
        plt.show()

if __name__ == '__main__':
    test_extraction() 