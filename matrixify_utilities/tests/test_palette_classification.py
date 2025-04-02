from utils.color_utils import ColorExtractor, ColorInfo
from simple_extractor import GarmentParser
from palette_classifier import PaletteClassifier
import matplotlib.pyplot as plt
import os

def test_classification():
    # Initialize all components
    parser = GarmentParser(
        model_path='models/exp-schp-201908301523-atr.pth',
        dataset='atr'
    )
    color_extractor = ColorExtractor(n_colors=5, lab_threshold=30)
    palette_classifier = PaletteClassifier(use_rules=True)
    
    # Process images
    test_dir = 'data/test_img'
    image_files = [f for f in os.listdir(test_dir) 
                  if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    
    for image_file in image_files:
        process_image(os.path.join(test_dir, image_file), parser, color_extractor, palette_classifier)

def process_image(image_path, parser, color_extractor, classifier, category_path=None):
    """Process a single image and display classification results"""
    print(f"\nProcessing {image_path}...")
    
    # Extract colors using category-based mask
    result = parser.parse_image(image_path)
    
    # Get mask using category if provided
    if category_path:
        mask_info = parser.get_garment_mask_steps(result, category_path=category_path)
        mask = mask_info['final_mask']
        if parser.verbose:
            print("\nUsing category-based mask:", category_path)
            print("Selected classes:", mask_info['selected_classes'])
            
        # Visualize masked region
        plt.figure(figsize=(15, 5))
        
        # Original image
        plt.subplot(131)
        plt.imshow(result['original_image'])
        plt.title('Original Image')
        plt.axis('off')
        
        # Mask
        plt.subplot(132)
        plt.imshow(mask, cmap='gray')
        plt.title('Category Mask')
        plt.axis('off')
        
        # Masked image
        plt.subplot(133)
        masked_img = result['original_image'].copy()
        masked_img[mask == 0] = [255, 255, 255]  # White background
        plt.imshow(masked_img)
        plt.title('Masked Region')
        plt.axis('off')
        
        plt.tight_layout()
        plt.show()
    else:
        # Fallback to basic upper garment mask
        mask = parser.get_garment_mask(result, garment_type='upper')
    
    # Extract colors with more granular settings
    color_analysis = color_extractor.extract_colors(
        image_path, 
        mask,
        background_color=[255, 255, 255]  # Explicitly set background color
    )
    
    # Print color analysis
    print("\nColor Analysis:")
    for color in color_analysis['colors']:
        rgb = color.rgb
        freq = color.frequency
        lab = color.lab
        print(f"RGB{rgb} ({freq:.1f}%) - LAB: {lab}")
    
    # Get garment analysis and formatted results
    garment_analysis = classifier.classify_garment(
        color_analysis['colors'],
        primary_threshold=0.98,
        secondary_threshold=0.90,
        min_confidence=0.6,
        pattern_threshold=0.02
    )
    results = classifier.format_results(garment_analysis)
    
    print("\n=== Season Classification ===")
    
    # Show primary matches
    if results['primary_seasons']:
        print("\nPrimary Season Matches:")
        for season in results['primary_seasons']:
            score = results['scores'][season] * 100
            print(f"  {season.value}: {score:.1f}%")
    
    # Show characteristics explanation
    print("\nColor Characteristics:")
    for color in color_analysis['colors']:
        matches = classifier.classify_color(color)
        if matches:
            print(f"  {matches[0].explanation}")
            
    return color_analysis, results

def print_color_analysis(color: ColorInfo, classifier: PaletteClassifier):
    """Print detailed analysis of a color"""
    matches = classifier.classify_color(color)
    
    print(f"\nColor Analysis for RGB{color.rgb} (frequency: {color.frequency:.2%}):")
    print(f"LAB: {color.lab}")
    
    if matches:
        print("\nTop Matches:")
        # Calculate total confidence for normalization
        total_confidence = sum(match.confidence for match in matches)
        
        for match in matches:
            # Normalize confidence to percentage
            normalized_confidence = (match.confidence / total_confidence) * 100
            # Only show matches with >5% confidence
            if normalized_confidence >= 5.0:
                print(f"\n{match.season.value}: {normalized_confidence:.2f}%")
                print(f"Explanation: {match.explanation}")
    else:
        print("No confident matches found")

if __name__ == '__main__':
    # Initialize components
    parser = GarmentParser(
        model_path='models/exp-schp-201908301523-atr.pth',
        dataset='atr',
        verbose=True
    )
    
    color_extractor = ColorExtractor(
        n_colors=8,  # Increase number of colors
        lab_threshold=20,  # More sensitive color differentiation
        verbose=True
    )
    
    classifier = PaletteClassifier(use_rules=True)
    
    # Test image
    image_path = 'data/test_img/Pants.webp'
    category_path = "Apparel & Accessories > Clothing > Pants"
    
    # Process with category
    color_analysis, results = process_image(
        image_path, 
        parser, 
        color_extractor, 
        classifier,
        category_path=category_path
    ) 