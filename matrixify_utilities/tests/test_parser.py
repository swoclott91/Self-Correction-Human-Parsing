from simple_extractor import GarmentParser
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import cv2
import os

def analyze_garment_color(image_path, mask, color_refinement=True):
    """Analyze garment color with optional color-based refinement
    
    Args:
        image_path: Path to original image
        mask: Binary mask from garment parser
        color_refinement: Whether to apply color-based refinement
    
    Returns:
        dict containing:
        - dominant_color: (R,G,B) tuple of main garment color
        - refined_mask: Mask after color refinement
        - color_histogram: Distribution of colors in the garment
    """
    # Read image and apply mask
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Get initial masked region
    masked_img = img.copy()
    masked_img[mask == 0] = [0, 0, 0]
    
    if color_refinement:
        # Convert to LAB color space for better color similarity
        lab_img = cv2.cvtColor(masked_img, cv2.COLOR_RGB2LAB)
        
        # Get the mean color of the largest connected component
        coords = np.column_stack(np.where(mask > 0))
        if len(coords) > 0:
            center_y, center_x = np.mean(coords, axis=0).astype(int)
            center_color = lab_img[center_y, center_x]
            
            # Create color similarity mask
            color_diff = np.sqrt(np.sum((lab_img - center_color)**2, axis=2))
            color_mask = color_diff < 30  # Adjust threshold as needed
            
            # Combine with original mask
            refined_mask = (mask > 0) & color_mask
            
            # Apply refined mask
            masked_img = img.copy()
            masked_img[~refined_mask] = [0, 0, 0]
        else:
            refined_mask = mask
    else:
        refined_mask = mask
    
    # Get dominant color (excluding black background)
    pixels = masked_img[refined_mask > 0].reshape(-1, 3)
    if len(pixels) > 0:
        # Use k-means to find dominant colors
        pixels = np.float32(pixels)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, .1)
        flags = cv2.KMEANS_RANDOM_CENTERS
        _, labels, palette = cv2.kmeans(pixels, 5, None, criteria, 10, flags)
        
        # Get dominant color by frequency
        _, counts = np.unique(labels, return_counts=True)
        dominant_color = tuple(map(int, palette[np.argmax(counts)]))
    else:
        dominant_color = (0, 0, 0)
    
    return {
        'dominant_color': dominant_color,
        'refined_mask': refined_mask,
        'masked_image': masked_img
    }

def visualize_mask_steps(img, mask, classes, ax, title=None):
    """Visualize mask with colored overlays for different classes"""
    # Create color map for different classes (RGB format)
    color_map = {
        'Background': [128, 128, 128],  # Gray
        'Upper-clothes': [0, 255, 0],   # Green
        'Dress': [255, 0, 0],          # Red
        'Left-arm': [0, 0, 255],       # Blue
        'Right-arm': [0, 0, 255],      # Blue
        'Face': [255, 255, 0],         # Yellow
        'Hair': [255, 128, 0],         # Orange
        'Skirt': [255, 0, 255],        # Magenta
        'Pants': [0, 255, 255],        # Cyan
        'Left-leg': [128, 0, 0],       # Dark red
        'Right-leg': [0, 128, 0],      # Dark green
    }
    
    # Create visualization image
    vis_img = img.copy()
    alpha = 0.5
    
    # Create separate overlays for each class
    for class_name, color in color_map.items():
        if class_name in classes:
            class_idx = classes[class_name]
            class_mask = (mask == class_idx)
            if np.any(class_mask):
                overlay = np.zeros_like(img)
                overlay[class_mask] = color
                vis_img = cv2.addWeighted(vis_img, 1, overlay, alpha, 0)
    
    ax.imshow(vis_img)
    if title:
        ax.set_title(f"{title}\n{mask.shape}")
    ax.axis('off')
    
    # Add legend with correct RGB values
    legend_elements = [plt.Rectangle((0,0),1,1, fc=[r/255, g/255, b/255, alpha]) 
                      for r,g,b in color_map.values()]
    ax.legend(legend_elements, color_map.keys(), 
             loc='center left', bbox_to_anchor=(1, 0.5))

def debug_component_analysis(img, mask, stats, labels, centroids, ax):
    """Visualize connected components analysis"""
    vis_img = img.copy()
    
    # Generate random colors for components
    num_labels = len(np.unique(labels))
    colors = np.random.randint(0, 255, size=(num_labels, 3), dtype=np.uint8)
    colors[0] = [0, 0, 0]  # Background is black
    
    # Create component overlay
    component_overlay = np.zeros_like(img)
    for i in range(1, num_labels):
        component_mask = (labels == i)
        component_overlay[component_mask] = colors[i]
        
        # Draw bounding box
        x, y, w, h, area = stats[i]
        cv2.rectangle(vis_img, (x, y), (x+w, y+h), colors[i].tolist(), 2)
        
        # Draw centroid
        cx, cy = map(int, centroids[i])
        cv2.circle(vis_img, (cx, cy), 5, colors[i].tolist(), -1)
        
        # Add component info
        ax.text(x, y-5, f'Area: {area}', color='white', 
                bbox=dict(facecolor='black', alpha=0.7))
    
    # Blend component overlay with image
    alpha = 0.5
    vis_img = cv2.addWeighted(vis_img, 1, component_overlay, alpha, 0)
    
    ax.imshow(vis_img)
    ax.set_title('Connected Components Analysis')
    ax.axis('off')

def test_parser():
    parser = GarmentParser(
        model_path='models/exp-schp-201908301523-atr.pth',
        dataset='atr'
    )
    
    test_dir = 'data/test_img'
    image_files = [f for f in os.listdir(test_dir) 
                  if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    
    for image_file in image_files:
        print(f"\nProcessing {image_file}...")
        image_path = os.path.join(test_dir, image_file)
        
        # Load image and get dimensions
        img = plt.imread(image_path)
        h, w = img.shape[:2]
        print(f"Original image dimensions: {w}x{h}")
        
        # Parse image
        result = parser.parse_image(image_path)
        print(f"Parsed mask dimensions: {result['mask'].shape}")
        
        # Verify mask dimensions match image
        if result['mask'].shape[:2] != (h, w):
            print("WARNING: Mask dimensions don't match image dimensions!")
            # Resize mask to match image dimensions
            result['mask'] = cv2.resize(result['mask'], (w, h), 
                                      interpolation=cv2.INTER_NEAREST)
        
        # Create figure for detailed mask analysis
        fig = plt.figure(figsize=(20, 10))
        gs = fig.add_gridspec(2, 3)
        
        # Original image
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.imshow(img)
        ax1.set_title(f'Original Image {img.shape}')
        ax1.axis('off')
        
        # Raw segmentation mask
        ax2 = fig.add_subplot(gs[0, 1])
        visualize_mask_steps(img, result['mask'], result['classes'], ax2, 'Raw Segmentation')
        
        # Get garment mask steps
        mask_steps = parser.get_garment_mask_steps(result, garment_type='upper')
        
        # Initial garment mask
        ax3 = fig.add_subplot(gs[0, 2])
        ax3.imshow(mask_steps['initial_mask'], cmap='gray')
        ax3.set_title('Initial Garment Mask')
        ax3.axis('off')
        
        # Exclusion regions
        ax4 = fig.add_subplot(gs[1, 0])
        ax4.imshow(mask_steps['exclude_mask'], cmap='gray')
        ax4.set_title('Exclusion Regions')
        ax4.axis('off')
        
        # After exclusion
        ax5 = fig.add_subplot(gs[1, 1])
        ax5.imshow(mask_steps['after_exclusion'], cmap='gray')
        ax5.set_title('After Exclusion')
        ax5.axis('off')
        
        # Component analysis
        ax6 = fig.add_subplot(gs[1, 2])
        # Get connected components of the after_exclusion mask
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            mask_steps['after_exclusion'].astype(np.uint8), 8, cv2.CV_32S)
        debug_component_analysis(img, mask_steps['after_exclusion'], 
                               stats, labels, centroids, ax6)
        
        plt.tight_layout()
        plt.show()
        
        # Print statistics
        print("\nMask Statistics:")
        print(f"Image size: {img.shape[:2]}")
        print(f"Initial mask coverage: {np.mean(mask_steps['initial_mask'])*100:.1f}%")
        print(f"Final mask coverage: {np.mean(mask_steps['final_mask'])*100:.1f}%")
        print(f"Number of components: {num_labels-1}")  # Subtract 1 for background
        
        if mask_steps.get('is_dress'):
            print("Detected as dress")
        else:
            print("Detected as upper clothes")

if __name__ == '__main__':
    test_parser() 