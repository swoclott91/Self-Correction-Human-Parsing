import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from simple_extractor import GarmentParser
from utils.color_utils import ColorExtractor
from PIL import Image

def visualize_category_segmentation(image_path, category_path=None):
    """
    Visualize how category affects segmentation for a single image.
    
    Args:
        image_path: Path to the image file
        category_path: Optional category path (e.g. "Apparel & Accessories > Clothing > One-Pieces")
    """
    # Initialize parser
    parser = GarmentParser(
        model_path='models/exp-schp-201908301523-atr.pth',
        dataset='atr',
        verbose=True
    )
    
    # Load and parse image using PIL first
    img_pil = Image.open(image_path).convert('RGB')
    img = np.array(img_pil)  # Convert PIL image to numpy array
    result = parser.parse_image(image_path)
    
    # Create figure
    plt.figure(figsize=(20, 15))
    gs = GridSpec(3, 3)
    
    # Original image
    plt.subplot(gs[0, 0])
    plt.imshow(img)
    plt.title('Original Image')
    plt.axis('off')
    
    # Raw segmentation mask with colormap
    plt.subplot(gs[0, 1])
    seg_mask = plt.imshow(result['mask'], cmap='tab20')
    plt.colorbar(seg_mask)
    plt.title('Raw Segmentation\n(Class IDs)')
    plt.axis('off')
    
    # Class distribution
    plt.subplot(gs[0, 2])
    unique_classes, counts = np.unique(result['mask'], return_counts=True)
    class_names = {i: name for i, name in enumerate(result['classes'])}
    class_info = []
    for cls, count in zip(unique_classes, counts):
        if cls in class_names:
            percentage = (count / result['mask'].size) * 100
            class_info.append(f"Class {cls} ({class_names[cls]}): {percentage:.1f}%")
    plt.text(0.1, 0.5, '\n'.join(class_info), fontsize=10)
    plt.title('Class Distribution')
    plt.axis('off')
    
    # Get masks with debug info
    print("\nGetting basic mask...")
    basic_mask_info = parser.get_garment_mask_steps(result)
    basic_mask = basic_mask_info['final_mask']
    
    print("\nGetting category mask...")
    try:
        category_mask_info = parser.get_garment_mask_steps(result, category_path=category_path)
        category_mask = category_mask_info['final_mask']
    except Exception as e:
        print(f"Error getting category mask: {str(e)}")
        print("Falling back to basic mask...")
        category_mask_info = basic_mask_info
        category_mask = basic_mask
    
    # Print class mapping info
    print("\nClass Mapping:")
    class_names = {i: name for i, name in enumerate(result['classes'])}
    print("\nAvailable classes:")
    for cls_id, name in class_names.items():
        count = np.sum(result['mask'] == cls_id)
        if count > 0:
            percentage = (count / result['mask'].size) * 100
            print(f"Class {cls_id} ({name}): {percentage:.1f}% of image")
    
    # Basic garment mask
    plt.subplot(gs[1, 0])
    plt.imshow(basic_mask, cmap='gray')
    plt.title('Basic Garment Mask\n(No Category)')
    plt.axis('off')
    
    # Show selected classes for basic mask
    plt.subplot(gs[1, 1])
    basic_selected = np.zeros_like(result['mask'])
    if 'selected_classes' in basic_mask_info:
        for cls in basic_mask_info['selected_classes']:
            basic_selected[result['mask'] == cls] = cls
    plt.imshow(basic_selected, cmap='tab20')
    plt.title('Selected Classes\n(Basic Mask)')
    plt.colorbar()
    plt.axis('off')
    
    # Category-based mask
    plt.subplot(gs[2, 0])
    plt.imshow(category_mask, cmap='gray')
    plt.title(f'Category-based Mask\n({category_path or "None"})')
    plt.axis('off')
    
    # Show selected classes for category mask
    plt.subplot(gs[2, 1])
    category_selected = np.zeros_like(result['mask'])
    if 'selected_classes' in category_mask_info:
        for cls in category_mask_info['selected_classes']:
            category_selected[result['mask'] == cls] = cls
    plt.imshow(category_selected, cmap='tab20')
    plt.title('Selected Classes\n(Category Mask)')
    plt.colorbar()
    plt.axis('off')
    
    # Difference visualization
    plt.subplot(gs[2, 2])
    diff_mask = np.zeros_like(basic_mask, dtype=np.uint8)
    diff_mask[basic_mask != category_mask] = 255
    plt.imshow(diff_mask, cmap='hot')
    plt.title('Mask Differences\n(Red shows changes)')
    plt.axis('off')
    
    # Print debug info
    print("\nMask Generation Debug Info:")
    print("\nBasic Mask Info:")
    for key, value in basic_mask_info.items():
        if key != 'final_mask':
            print(f"{key}: {value}")
            
    print("\nCategory Mask Info:")
    for key, value in category_mask_info.items():
        if key != 'final_mask':
            print(f"{key}: {value}")
    
    plt.tight_layout()
    
    # Save visualization
    save_path = os.path.join('debug_visualizations', f'category_test_{os.path.basename(image_path)}.png')
    os.makedirs('debug_visualizations', exist_ok=True)
    plt.savefig(save_path, bbox_inches='tight', dpi=300)
    print(f"\nVisualization saved to {save_path}")
    plt.show()

if __name__ == '__main__':
    # Test image path
    test_img_dir = r"C:\Users\Shane Work\Documents\GitHub\Self-Correction-Human-Parsing\data\test_img"
    test_image = "Pants.webp"
    image_path = os.path.join(test_img_dir, test_image)
    
    # Extract category from filename
    category = os.path.splitext(test_image)[0]
    category_path = f"Apparel & Accessories > Clothing > {category}"
    
    print(f"Testing image: {image_path}")
    print(f"Using category: {category_path}")
    
    visualize_category_segmentation(image_path, category_path) 