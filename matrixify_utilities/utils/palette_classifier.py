from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, NamedTuple
from enum import Enum
import numpy as np
import cv2
from utils.color_utils import ColorInfo
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ColorAnalysis(NamedTuple):
    """Detailed analysis of a color's characteristics"""
    temperature: float
    brightness: float
    depth: float
    chroma: float
    lightness: float
    is_neutral: bool
    quadrant: str
    explanation: str

class SeasonMatch(NamedTuple):
    """A season match with confidence and explanation"""
    season: 'Season'
    confidence: float
    explanation: str

class Season(Enum):
    SPRING_BRIGHT = "Bright Spring"
    SPRING_LIGHT = "Light Spring"
    SPRING_WARM = "Warm Spring"
    SUMMER_LIGHT = "Light Summer"
    SUMMER_SOFT = "Soft Summer"
    SUMMER_COOL = "Cool Summer"
    AUTUMN_WARM = "Warm Autumn"
    AUTUMN_SOFT = "Soft Autumn"
    AUTUMN_DEEP = "Deep Autumn"
    WINTER_DEEP = "Deep Winter"
    WINTER_COOL = "Cool Winter"
    WINTER_BRIGHT = "Bright Winter"

@dataclass
class SeasonalCharacteristics:
    temperature: float  # Cool (-1) to Warm (+1)
    brightness: float  # Soft (-1) to Bright (+1)
    depth: float      # Light (-1) to Deep (+1)
    
    def __str__(self):
        return (
            f"Temperature: {self.temperature:+.2f} "
            f"({'Warm' if self.temperature > 0 else 'Cool'}), "
            f"Brightness: {self.brightness:+.2f} "
            f"({'Bright' if self.brightness > 0 else 'Soft'}), "
            f"Depth: {self.depth:+.2f} "
            f"({'Deep' if self.depth > 0 else 'Light'})"
        )

class PaletteClassifier:
    # Thresholds for rule-based classification
    STRONG_WARM = 0.8
    STRONG_COOL = -0.8
    VERY_BRIGHT = 0.8
    VERY_SOFT = -0.8
    VERY_DEEP = 0.8
    VERY_LIGHT = -0.8
    NEUTRAL_CHROMA = 0.2

    def __init__(self, use_rules: bool = True, sigma: float = 25.0):
        """Initialize classifier
        
        Args:
            use_rules: Whether to use rule-based classification
            sigma: Standard deviation for Gaussian weighting (in LAB units)
        """
        self.use_rules = use_rules
        self.sigma = sigma
        # Reference colors for each season (RGB values)
        self.reference_colors = {
            # Springs: Warm and Clear
            Season.SPRING_BRIGHT: [
                (255, 122, 0),  # Bright Orange
                (255, 196, 0),  # Sunny Yellow
                (255, 128, 142), # Coral Pink
            ],
            Season.SPRING_LIGHT: [
                (255, 190, 190), # Light Pink
                (255, 222, 179), # Peach
                (255, 250, 179), # Light Yellow
            ],
            Season.SPRING_WARM: [
                (255, 166, 102), # Warm Peach
                (255, 214, 102), # Golden Yellow
                (255, 159, 159), # Warm Pink
            ],
            
            # Summers: Cool and Soft
            Season.SUMMER_LIGHT: [
                (182, 219, 255), # Light Blue
                (255, 182, 193), # Light Pink
                (176, 224, 230), # Powder Blue
            ],
            Season.SUMMER_SOFT: [
                (140, 170, 190), # Soft Blue
                (190, 160, 170), # Mauve
                (170, 190, 180), # Sage
            ],
            Season.SUMMER_COOL: [
                (100, 150, 200), # Cool Blue
                (180, 140, 160), # Cool Pink
                (130, 170, 170), # Cool Aqua
            ],
            
            # Autumns: Warm and Muted
            Season.AUTUMN_WARM: [
                (200, 120, 60),  # Rust
                (180, 130, 80),  # Camel
                (150, 100, 50),  # Brown
            ],
            Season.AUTUMN_SOFT: [
                (160, 140, 100), # Olive
                (170, 120, 100), # Soft Brown
                (140, 110, 90),  # Taupe
            ],
            Season.AUTUMN_DEEP: [
                (130, 70, 40),   # Deep Brown
                (100, 50, 30),   # Auburn
                (80, 40, 20),    # Dark Brown
            ],
            
            # Winters: Cool and Clear
            Season.WINTER_DEEP: [
                (0, 0, 128),     # Navy
                (128, 0, 64),    # Deep Wine
                (0, 64, 128),    # Deep Blue
            ],
            Season.WINTER_COOL: [
                (0, 100, 150),   # Cool Blue
                (150, 0, 100),   # Cool Purple
                (0, 128, 128),   # Teal
            ],
            Season.WINTER_BRIGHT: [
                (0, 150, 255),   # Bright Blue
                (255, 0, 150),   # Bright Pink
                (0, 200, 200),   # Bright Turquoise
            ],
        }
        
        # Calculate season characteristics from reference colors
        self.season_profiles = {}
        for season, colors in self.reference_colors.items():
            chars = []
            for rgb in colors:
                # Create ColorInfo object with color conversions
                lab = self._rgb_to_lab(rgb)
                hsv = self._rgb_to_hsv(rgb)
                color_info = ColorInfo(
                    rgb=rgb,
                    hex=self._rgb_to_hex(rgb),
                    lab=lab,
                    hsv=hsv,
                )
                chars.append(self._calculate_color_characteristics(color_info))
            
            # Average the characteristics
            self.season_profiles[season] = SeasonalCharacteristics(
                temperature=sum(c.temperature for c in chars) / len(chars),
                brightness=sum(c.brightness for c in chars) / len(chars),
                depth=sum(c.depth for c in chars) / len(chars)
            )

    @staticmethod
    def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex string"""
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    @staticmethod
    def _rgb_to_lab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
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
    def _rgb_to_hsv(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """Convert RGB to HSV color space"""
        bgr = np.uint8([[list(reversed(rgb))]])
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0][0]
        return tuple(map(float, hsv))

    def _calculate_color_characteristics(self, color: ColorInfo) -> ColorAnalysis:
        """Calculate color characteristics using weighted averaging"""
        L, a, b = color.lab
        
        # Calculate chroma
        chroma = np.sqrt(a*a + b*b) / 181
        
        # Calculate temperature using weighted contribution of a/b
        a_weight = abs(a) / (abs(a) + abs(b)) if (abs(a) + abs(b)) > 0 else 0.5
        b_weight = 1 - a_weight
        
        temperature = (
            (a * a_weight / 127) +  # Red-green contribution
            (b * b_weight / 127)    # Yellow-blue contribution
        )
        
        # Calculate other characteristics
        brightness = self._calculate_brightness(L, chroma)
        depth = self._calculate_depth(L)
        
        # Determine quadrant with soft boundaries
        is_neutral = chroma < self.NEUTRAL_CHROMA
        if is_neutral:
            if temperature > 0.2:
                quadrant = "Neutral-warm zone"
            elif temperature < -0.2:
                quadrant = "Neutral-cool zone"
            else:
                quadrant = "Neutral zone"
        else:
            if temperature > 0.2:
                quadrant = "Warm zone"
            elif temperature < -0.2:
                quadrant = "Cool zone"
            else:
                quadrant = "Neutral zone"
        
        return ColorAnalysis(
            temperature=temperature,
            brightness=brightness,
            depth=depth,
            chroma=chroma,
            lightness=L/100,
            is_neutral=is_neutral,
            quadrant=quadrant,
            explanation=f"LAB: ({L:.1f}, {a:.1f}, {b:.1f})"
        )

    def _calculate_season_similarity(self, color_chars: SeasonalCharacteristics, season_chars: SeasonalCharacteristics) -> float:
        """Calculate how well a color matches a season's characteristics using perceptual color differences"""
        
        # Calculate Delta E for reference colors
        def calculate_delta_e(lab1, lab2):
            # Use CIE94 color difference formula
            L1, a1, b1 = lab1
            L2, a2, b2 = lab2
            
            dL = L1 - L2
            da = a1 - a2
            db = b1 - b2
            
            C1 = np.sqrt(a1*a1 + b1*b1)
            C2 = np.sqrt(a2*a2 + b2*b2)
            dC = C1 - C2
            
            dH = np.sqrt(da*da + db*db - dC*dC)
            
            # Weighting factors
            kL = 1  # Lightness
            kC = 1  # Chroma 
            kH = 1  # Hue
            
            # Calculate similarity
            L_term = (dL / (kL))**2
            C_term = (dC / (kC))**2
            H_term = (dH / (kH))**2
            
            delta_e = np.sqrt(L_term + C_term + H_term)
            return delta_e
        
        # Weight the characteristics
        temp_weight = 2.0
        bright_weight = 1.2
        depth_weight = 0.8
        
        # Calculate perceptual differences
        temp_diff = calculate_delta_e(
            [color_chars.temperature * 50 + 50, 0, 0],
            [season_chars.temperature * 50 + 50, 0, 0]
        )
        
        bright_diff = calculate_delta_e(
            [color_chars.brightness * 50 + 50, 0, 0],
            [season_chars.brightness * 50 + 50, 0, 0]
        )
        
        depth_diff = calculate_delta_e(
            [color_chars.depth * 50 + 50, 0, 0],
            [season_chars.depth * 50 + 50, 0, 0]
        )
        
        # Calculate weighted similarity
        total_diff = (
            temp_weight * temp_diff +
            bright_weight * bright_diff +
            depth_weight * depth_diff
        )
        
        # Convert to similarity score
        similarity = 1.0 / (1.0 + total_diff/100)
        return max(0, min(0.95, similarity))

    def _calculate_gaussian_weight(self, delta_e: float) -> float:
        """Calculate Gaussian weight based on Delta E distance
        
        Args:
            delta_e: Color difference in LAB space
            
        Returns:
            Confidence score between 0-100
        """
        # More aggressive scaling and normalization
        scaled_delta_e = delta_e / 2.0  # Base scaling factor
        
        # Calculate base confidence with quadratic falloff
        confidence = np.exp(-(scaled_delta_e ** 2) / (2 * self.sigma ** 2))
        
        # Convert to percentage
        confidence = confidence * 100
        
        return np.clip(confidence, 0, 100)

    def classify_color(self, color: ColorInfo, min_confidence: float = 10.0) -> List[SeasonMatch]:
        """Classify a color using soft membership scoring
        
        Args:
            color: Color to classify
            min_confidence: Minimum confidence threshold (default 10%)
            
        Returns:
            List of season matches above threshold confidence
        """
        matches = []
        total_confidence = 0
        raw_matches = []
        
        # Calculate characteristics
        analysis = self._calculate_color_characteristics(color)
        
        # First pass - calculate raw matches and total confidence
        for season in Season:
            ref_colors = self.reference_colors[season]
            
            # Calculate minimum Delta E distance to any reference color
            min_delta_e = float('inf')
            for ref_color in ref_colors:
                ref_lab = self._rgb_to_lab(ref_color)
                delta_e = self.calculate_delta_e(color.lab, ref_lab)
                min_delta_e = min(min_delta_e, delta_e)
            
            # Calculate raw confidence
            confidence = self._calculate_gaussian_weight(min_delta_e)
            total_confidence += confidence
            
            if confidence >= min_confidence:
                raw_matches.append((season, confidence, self.season_profiles[season]))
        
        # Second pass - normalize confidences
        if total_confidence > 0:
            for season, confidence, characteristics in raw_matches:
                # Normalize confidence to percentage
                normalized_confidence = (confidence / total_confidence) * 100
                
                # Create explanation
                explanation = (
                    f"Matches {season.value} characteristics: "
                    f"{characteristics}. "
                    f"Analysis: {analysis.quadrant}, "
                    f"{analysis.explanation}"
                )
                
                matches.append(SeasonMatch(
                    season=season,
                    confidence=normalized_confidence,
                    explanation=explanation
                ))
        
        # Sort by confidence
        matches.sort(key=lambda x: x.confidence, reverse=True)
        
        # Only return top 3 matches if we have many high confidence matches
        if len(matches) > 3 and matches[0].confidence > 80:
            matches = matches[:3]
        
        return matches

    def classify_garment(self, colors: List[ColorInfo], 
                        primary_threshold: float = 0.05,   
                        pattern_threshold: float = 0.02,   
                        min_confidence: float = 0.6,
                        secondary_threshold: float = 0.02):
        """Classify a garment using weighted color analysis
        
        Args:
            colors: List of colors to analyze
            primary_threshold: Threshold for primary colors (default 5%)
            pattern_threshold: Threshold for pattern detection (default 2%)
            min_confidence: Minimum confidence for color matches (default 60%)
            secondary_threshold: Threshold for secondary colors (default 2%)
        """
        # Initialize membership scores
        season_scores = {season: 0.0 for season in Season}
        
        # Track colors and weights
        color_analyses = []
        total_weight = 0.0
        
        # First pass - analyze colors and calculate weights
        for color in colors:
            matches = self.classify_color(color, min_confidence)
            base_weight = self._calculate_color_weight(color)
            final_weight = base_weight * (color.frequency / 100.0)
            
            color_analyses.append({
                'color': color,
                'matches': matches,
                'weight': final_weight
            })
            total_weight += final_weight
        
        # Second pass - calculate normalized scores
        for analysis in color_analyses:
            normalized_weight = analysis['weight'] / total_weight
            
            # Get total confidence for normalization
            total_confidence = sum(match.confidence for match in analysis['matches'])
            
            # Add weighted, normalized contributions
            for match in analysis['matches']:
                normalized_confidence = match.confidence / total_confidence
                season_scores[match.season] += normalized_confidence * normalized_weight
        
        # Ensure scores sum to 1.0
        total_score = sum(season_scores.values())
        if total_score > 0:
            season_scores = {
                season: (score / total_score)
                for season, score in season_scores.items()
            }
        
        return {
            'season_scores': season_scores,
            'color_analyses': color_analyses
        }

    def _calculate_brightness(self, L: float, chroma: float) -> float:
        """Calculate brightness characteristic from lightness and chroma"""
        normalized_L = L/100
        
        if chroma < 0.5:  # For muted colors
            brightness = (normalized_L * 0.5 + chroma * 0.5) * 2 - 1
            brightness *= (1 - (0.5 - chroma))  # Further reduce brightness for muted colors
        else:
            brightness = (normalized_L * 0.7 + chroma * 0.3) * 2 - 1
        
        return np.clip(brightness, -1, 1)

    def _calculate_depth(self, L: float) -> float:
        """Calculate depth characteristic from lightness"""
        normalized_L = L/100
        depth = (1.0 - normalized_L) * 2 - 1
        return np.clip(depth, -1, 1)

    def calculate_delta_e(self, lab1: Tuple[float, float, float], 
                         lab2: Tuple[float, float, float]) -> float:
        """Calculate CIE94 color difference between two LAB colors"""
        L1, a1, b1 = lab1
        L2, a2, b2 = lab2
        
        dL = L1 - L2
        da = a1 - a2
        db = b1 - b2
        
        C1 = np.sqrt(a1*a1 + b1*b1)
        C2 = np.sqrt(a2*a2 + b2*b2)
        dC = C1 - C2
        
        dH = np.sqrt(da*da + db*db - dC*dC)
        
        # Weighting factors
        kL = 1  # Lightness
        kC = 1  # Chroma 
        kH = 1  # Hue
        
        # Calculate similarity
        L_term = (dL / (kL))**2
        C_term = (dC / (kC))**2
        H_term = (dH / (kH))**2
        
        return np.sqrt(L_term + C_term + H_term)

    def _calculate_color_weight(self, color: ColorInfo) -> float:
        """Calculate weight for a color based on its characteristics
        
        Higher weights for:
        - More saturated colors
        - Colors closer to reference colors
        """
        L, a, b = color.lab
        
        # Calculate chroma (saturation)
        chroma = np.sqrt(a*a + b*b) / 181  # Already normalized 0-1
        
        # Higher weight for more saturated colors
        saturation_weight = 0.5 + 0.5 * chroma
        
        # Find closest reference color
        min_delta_e = float('inf')
        for season in Season:
            for ref_color in self.reference_colors[season]:
                ref_lab = self._rgb_to_lab(ref_color)
                delta_e = self.calculate_delta_e(color.lab, ref_lab)
                min_delta_e = min(min_delta_e, delta_e)
        
        # Convert minimum delta E to a weight (closer = higher weight)
        reference_weight = self._calculate_gaussian_weight(min_delta_e) / 100  # Normalize to 0-1
        
        # Combine weights
        return (saturation_weight + reference_weight) / 2.0

    def analyze_garment_colors(self, colors_with_frequencies):
        """Analyze garment colors and determine seasonal matches.
        
        Args:
            colors_with_frequencies: List of (RGB, frequency) tuples
        """
        # Normalize frequencies to sum to 1.0
        total_freq = sum(freq for _, freq in colors_with_frequencies)
        normalized_colors = [(color, freq/total_freq) for color, freq in colors_with_frequencies]
        
        # Analyze each color
        color_analyses = []
        for rgb, frequency in normalized_colors:
            # Get base confidence for this color
            base_weight = self._calculate_color_weight(rgb)
            
            # Calculate final weight (combine base weight with frequency)
            final_weight = base_weight * frequency
            
            # Get season matches
            matches = self.classify_color(rgb)
            
            color_analyses.append({
                'rgb': rgb,
                'frequency': frequency,
                'base_weight': base_weight,
                'final_weight': final_weight,
                'matches': matches
            })
        
        # Aggregate season scores using weighted average
        season_scores = defaultdict(float)
        total_weight = sum(analysis['final_weight'] for analysis in color_analyses)
        
        for analysis in color_analyses:
            weight = analysis['final_weight'] / total_weight  # Normalize weight
            for season, confidence in analysis['matches'].items():
                # Add weighted contribution
                season_scores[season] += confidence * weight
        
        # Normalize final scores to 0-1 range
        max_score = max(season_scores.values())
        normalized_scores = {
            season: score/max_score 
            for season, score in season_scores.items()
        }
        
        return {
            'color_analyses': color_analyses,
            'season_scores': normalized_scores
        }

    def format_results(self, analysis_results, 
                      primary_threshold=0.98,    # Scores within 2% of max
                      secondary_threshold=0.90):  # Scores within 10% of max
        """Format analysis results for product tagging.
        
        Returns:
            dict containing:
            - primary_seasons: List of seasons to use as primary tags
            - secondary_seasons: List of seasons to use as secondary tags
            - scores: Full scoring details
        """
        scores = analysis_results['season_scores']
        max_score = max(scores.values())
        
        # Find primary and secondary matches
        primary_seasons = [
            season 
            for season, score in scores.items()
            if score >= max_score * primary_threshold
        ]
        
        secondary_seasons = [
            season
            for season, score in scores.items()
            if max_score * secondary_threshold <= score < max_score * primary_threshold
        ]
        
        return {
            'primary_seasons': primary_seasons,
            'secondary_seasons': secondary_seasons,
            'scores': scores
        } 