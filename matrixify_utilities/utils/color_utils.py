import cv2
import numpy as np
from typing import Tuple, Dict, List, Union
from dataclasses import dataclass
from sklearn.cluster import KMeans

@dataclass
class ColorInfo:
    rgb: Tuple[int, int, int]
    hex: str
    lab: Tuple[float, float, float]
    hsv: Tuple[float, float, float]
    frequency: float = 1.0
    is_pattern: bool = False
    pattern_group: int = 0  # 0 means no pattern, positive numbers group related pattern colors

class ColorExtractor:
    def __init__(self, n_colors=5, lab_threshold=30, verbose=True):
        """Initialize color extractor
        
        Args:
            n_colors: Number of colors to extract
            lab_threshold: Threshold for merging similar colors in LAB space
            verbose: Whether to print debug information
        """
        self.n_colors = n_colors
        self.lab_threshold = lab_threshold
        self.verbose = verbose

    @staticmethod
    def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex string"""
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    @staticmethod
    def rgb_to_lab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """Convert RGB to LAB color space"""
        # Convert to BGR for OpenCV
        bgr = np.uint8([[list(reversed(rgb))]])
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[0][0]
        
        # Convert from OpenCV ranges to standard LAB ranges
        L = lab[0] * 100.0 / 255.0
        a = lab[1] - 128.0
        b = lab[2] - 128.0
        
        return (L, a, b)

    @staticmethod
    def rgb_to_hsv(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """Convert RGB to HSV color space"""
        bgr = np.uint8([[list(reversed(rgb))]])
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0][0]
        return tuple(map(float, hsv))

    def extract_colors(self, image_path, mask=None):
        """Extract dominant colors from an image"""
        # Load image
        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Apply mask if provided
        if mask is not None:
            img = cv2.bitwise_and(img, img, mask=mask)
        
        # Get valid pixels
        valid_pixels = img[mask > 0] if mask is not None else img.reshape(-1, 3)
        
        if len(valid_pixels) == 0:
            if self.verbose:
                print("No valid pixels found in mask")
            return {'colors': []}
        
        # Cluster colors
        kmeans = KMeans(n_clusters=self.n_colors)
        kmeans.fit(valid_pixels)
        
        # Get color frequencies
        colors = []
        labels = kmeans.labels_
        centers = kmeans.cluster_centers_
        
        for i in range(self.n_colors):
            # Get frequency
            freq = np.sum(labels == i) / len(labels) * 100
            
            if freq > 0:
                rgb = tuple(map(int, centers[i]))
                color_info = ColorInfo(rgb=rgb)
                
                # Check if similar to existing color
                merged = False
                for existing_color in colors:
                    if self.calculate_color_distance(color_info.lab, existing_color.lab) < self.lab_threshold:
                        existing_color.frequency += freq
                        merged = True
                        if self.verbose:
                            print(f"Merged with existing group: RGB{existing_color.rgb}")
                        break
                
                if not merged:
                    color_info.frequency = freq
                    colors.append(color_info)
                    if self.verbose:
                        print(f"Added as new color group: RGB{rgb}")
                        
        # Sort by frequency
        colors.sort(key=lambda x: x.frequency, reverse=True)
        
        # Filter out likely background colors
        colors = [c for c in colors if not self._is_background_color(c)]
        
        return {'colors': colors}

    def calculate_color_distance(self, lab1, lab2):
        # Implement the logic to calculate the distance between two LAB colors
        # This is a placeholder and should be replaced with the actual implementation
        return np.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))

    def _is_background_color(self, color_info):
        # Implement the logic to determine if a color is likely a background color
        # This is a placeholder and should be replaced with the actual implementation
        return False

    def extract_colors(self, 
                      image_path: str, 
                      mask: np.ndarray, 
                      background_color=None,
                      refine: bool = True) -> Dict[str, Union[List[ColorInfo], np.ndarray]]:
        """Extract dominant colors from masked region of image"""
        # Read and convert image
        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Apply initial mask
        masked_img = img.copy()
        masked_img[mask == 0] = [0, 0, 0]
        
        # Extract colors using k-means
        pixels = masked_img[mask > 0].reshape(-1, 3)
        colors = []
        
        if len(pixels) > 0:
            pixels = np.float32(pixels)
            
            # Use fewer initial clusters
            initial_clusters = min(self.n_colors, 6)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, .1)
            flags = cv2.KMEANS_RANDOM_CENTERS
            _, labels, palette = cv2.kmeans(pixels, initial_clusters, None, criteria, 10, flags)
            
            # Calculate initial color frequencies
            unique_labels, counts = np.unique(labels, return_counts=True)
            frequencies = counts / counts.sum()
            
            # Group similar colors
            grouped_colors = []
            
            # Debug: Print background color if available
            if background_color is not None:
                print(f"\nBackground color: RGB{tuple(map(int, background_color))}")
                bg_lab = self.rgb_to_lab(tuple(map(int, background_color)))
                bg_hsv = self.rgb_to_hsv(tuple(map(int, background_color)))
                print(f"Background HSV: ({int(bg_hsv[0])}°, {int(bg_hsv[1])}%, {int(bg_hsv[2])})")
            
            for color_idx, freq in zip(unique_labels, frequencies):
                rgb = tuple(map(int, palette[color_idx]))
                lab = self.rgb_to_lab(rgb)
                hsv = self.rgb_to_hsv(rgb)
                
                # Debug: Print color being analyzed
                print(f"\nAnalyzing color: RGB{rgb}")
                print(f"HSV: ({int(hsv[0])}°, {int(hsv[1])}%, {int(hsv[2])})")
                
                # Skip if too similar to background color
                if background_color is not None:
                    # Calculate color differences in both LAB and HSV space
                    lab_diff = np.sqrt(sum((a - b) ** 2 for a, b in zip(lab, bg_lab)))
                    
                    # Calculate hue difference considering circular nature
                    hue_diff = min(abs(hsv[0] - bg_hsv[0]), 
                                 360 - abs(hsv[0] - bg_hsv[0]))
                    sat_diff = abs(hsv[1] - bg_hsv[1])
                    val_diff = abs(hsv[2] - bg_hsv[2])
                    
                    print(f"LAB difference: {lab_diff:.1f}")
                    print(f"Hue difference: {hue_diff:.1f}°")
                    print(f"Saturation difference: {sat_diff:.1f}")
                    print(f"Value difference: {val_diff:.1f}")
                    
                    # More sophisticated background filtering:
                    # 1. Very similar in LAB space AND similar saturation
                    # 2. Similar hue, saturation, AND value
                    # 3. Exception: Keep high-frequency, high-saturation colors even if hue is similar
                    if ((lab_diff < 25 and sat_diff < 30) or  # Similar in LAB and saturation
                        (hue_diff < 15 and sat_diff < 30 and val_diff < 30)):  # Similar in HSV
                        # Exception: Keep high-frequency, saturated colors
                        if not (freq > 0.2 and hsv[1] > 100):
                            print("Skipped: Too similar to background")
                            continue
                        else:
                            print("Kept despite similarity: High frequency and saturation")
                
                # Filter out likely background colors
                s = hsv[1]  # Saturation
                v = hsv[2]  # Value
                if ((s < 30 and v > 200) or    # Very bright, low saturation
                    (v < 40) or                # Too dark
                    (s < 20 and freq < 0.05)): # Low saturation and low frequency
                    print("Skipped: Likely background color")
                    continue
                
                # Try to merge with existing group
                merged = False
                for group in grouped_colors:
                    group_lab = self.rgb_to_lab(group['rgb'])
                    delta_e = np.sqrt(sum((a - b) ** 2 for a, b in zip(lab, group_lab)))
                    
                    if delta_e < self.lab_threshold:
                        group['frequency'] += freq
                        merged = True
                        print(f"Merged with existing group: RGB{group['rgb']}")
                        break
                
                if not merged:
                    grouped_colors.append({
                        'rgb': rgb,
                        'frequency': freq,
                        'hsv': hsv
                    })
                    print("Added as new color group")
            
            # Normalize frequencies after filtering
            if grouped_colors:
                total_freq = sum(g['frequency'] for g in grouped_colors)
                for group in grouped_colors:
                    group['frequency'] = (group['frequency'] / total_freq) * 100
                    print(f"\nFinal color: RGB{group['rgb']} ({group['frequency']:.1f}%)")
            
            # Convert groups to ColorInfo objects and sort by frequency
            colors = [ColorInfo(
                rgb=group['rgb'],
                hex=self.rgb_to_hex(group['rgb']),
                lab=self.rgb_to_lab(group['rgb']),
                hsv=self.rgb_to_hsv(group['rgb']),
                frequency=group['frequency']
            ) for group in grouped_colors]
            
            colors.sort(key=lambda x: x.frequency, reverse=True)
        
        return {
            'colors': colors,
            'refined_mask': mask,
            'masked_image': masked_img,
            'has_pattern': False
        } 