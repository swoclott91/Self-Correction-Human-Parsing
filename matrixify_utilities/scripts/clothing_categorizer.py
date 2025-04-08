import re
from typing import Dict, List, Tuple, Optional, Union
import logging
from pathlib import Path
from .taxonomy_mapper import TaxonomyMapper
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ClothingCategorizer:
    """Categorizes clothing products into Shopify taxonomy paths"""
    
    # Simplified category keywords - just focus on identifying the category
    CATEGORY_KEYWORDS = {
        "Cardigans": [
            "cardigan", "open front", "button front sweater",
            "longline cardigan", "open cardigan", "duster cardigan"
        ],
        "T-Shirts": [
            "tee", "t-shirt", "t shirt", "tshirt", "crew neck tee"
        ],
        "Sweaters": [
            "sweater", "pullover", "jumper", "knit top"
        ],
        "Tops": [
            "top", "shirt", "blouse", "tank"
        ]
    }

    # Gender-specific clothing types
    FEMININE_CLOTHING = {
        'cardigan', 'blouse', 'dress', 'skirt', 'leggings', 'tunic',
        'camisole', 'tank top', 'maxi', 'midi', 'jumpsuit'
    }
    
    MASCULINE_CLOTHING = {
        'suit', 'tuxedo', 'blazer', 'necktie', 'bow tie'
    }

    # Update attribute patterns to match Shopify taxonomy attributes exactly
    ATTRIBUTE_PATTERNS = {
        "fabric": {  # ID: 2777
            "Polyester": r"(?:100%\s+)?polyester|poly(?:\s+blend)?",
            "Cotton": r"(?:100%\s+)?cotton|organic cotton",
            "Wool": r"(?:100%\s+)?wool|merino|cashmere",
            "Denim": r"denim|jean",
            "Linen": r"(?:100%\s+)?linen|flax",
            "Silk": r"(?:100%\s+)?silk",
            "Spandex": r"spandex|elastane|lycra",
            "Rayon": r"(?:100%\s+)?rayon|viscose"
        },
        "top-length-type": {  # ID: 1193
            "Cropped": r"crop(ped)?|short",
            "Regular": r"regular|standard|classic",
            "Long": r"long|maxi|full[-\s]length|longline",
            "Mini": r"mini|short|above[-\s]knee",
            "Midi": r"midi|mid[-\s]length|calf[-\s]length"
        },
        "sleeve-length-type": {  # ID: 15
            "Long Sleeve": r"long\s+sleeve|long-sleeve|full sleeve",
            "Short Sleeve": r"short\s+sleeve|short-sleeve|cap sleeve",
            "Three Quarter Sleeve": r"three[- ]quarter|3/4|three quarter",
            "Sleeveless": r"sleeveless|tank|camisole|strapless",
            
            # New patterns from taxonomy
            '3/4': r'3/4|three[- ]quarter',
            'cap': r'cap[- ]?sleeve',
            'long': r'long[- ]?sleeve|full[- ]?sleeve',
            'short': r'short[- ]?sleeve',
            'spaghetti strap': r'spaghetti[- ]strap',
            'strapless': r'strapless',
            'other': r'other',
        },
        "neckline": {  # ID: 32
            "V-neck": r"v[\s-]neck",
            "Crew": r"crew|round",
            "Scoop": r"scoop",
            "Boat": r"boat|bateau",
            "Cowl": r"cowl",
            "Asymmetric": r"asymmetric",
            "Bardot": r"bardot",
            "Halter": r"halter",
            "Hooded": r"hooded",
            "Mandarin": r"mandarin",
            "Mock": r"mock",
            "Plunging": r"plunging",
            "Round": r"round",
            "Split": r"split",
            "Square": r"square",
            "Sweetheart": r"sweetheart",
            "Turtle": r"turtle|turtleneck",
            "Wrap": r"wrap",
            "Other": r"other"
        },
        "target-gender": {  # ID: 837
            "Female": r"women'?s?|ladies?|female",
            "Male": r"men'?s?|male",
            "Unisex": r"unisex|gender neutral",
            "Other": r'other',
        },
        "age-group": {  # ID: 30
            "Adult": r"adult|grown[\s-]?up",
            "Teen": r"teen|adolescent",
            "Kids": r"kids?|children'?s?|youth",
            "Infant": r"infant|baby|newborn"
        },
        "clothing-features": {  # ID: 3001
            "Stretch": r"stretch|flexible|elastic",
            "Water Resistant": r"water[\s-]?resistant|waterproof",
            "Wrinkle Resistant": r"wrinkle[\s-]?free|no[\s-]iron"
        }
    }

    # Add common value variations
    VALUE_VARIATIONS = {
        'Stretchable': ['stretch', 'stretchy', 'elastic', 'flexible'],
        'Long': ['full length', 'maxi', 'longline', 'floor length'],
        'Short': ['cropped', 'crop', 'mini'],
        'Medium': ['mid length', 'midi', 'knee length'],
    }

    def __init__(self, taxonomy_dir: Optional[Path] = None):
        """Initialize with taxonomy directory"""
        self.mapper = TaxonomyMapper(taxonomy_dir)
        self._compile_category_patterns()

    def _compile_category_patterns(self) -> None:
        """Compile regex patterns for categories"""
        self.category_patterns = {}
        
        # Compile category patterns
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            patterns = []
            for keyword in keywords:
                pattern = re.compile(rf'\b{keyword}s?\b', re.IGNORECASE)
                patterns.append(pattern)
            self.category_patterns[category] = patterns

        # Compile attribute patterns
        self.attribute_patterns = {}
        for attr, values in self.ATTRIBUTE_PATTERNS.items():
            attr_patterns = {}
            for value, pattern in values.items():
                attr_patterns[value] = re.compile(pattern, re.IGNORECASE)
            self.attribute_patterns[attr] = attr_patterns

    def _score_category(self, text: str, title: str, patterns: List[re.Pattern]) -> float:
        """Score text for a category based on pattern matches"""
        score = 0
        
        # Check each pattern
        for pattern in patterns:
            # Base score for any match
            if pattern.search(text):
                score += 0.3
                
                # Boost for title matches
                if pattern.search(title):
                    score += 0.2
                    
                # Boost for exact matches
                if pattern.search(text).group().lower() == pattern.pattern.strip(r'\b').lower():
                    score += 0.2
                    
        return min(score, 1.0)

    def categorize(self, title: str, description: str = "") -> Tuple[str, float]:
        """
        Categorize a product based on its title and description
        Returns (category_path, confidence_score)
        """
        # Combine title and description, giving more weight to title
        text = f"{title} {title} {description}"
        
        best_category = None
        best_score = 0.1
        
        # Score against each category
        for category, patterns in self.category_patterns.items():
            score = self._score_category(text, title, patterns)
            
            if score > best_score:
                best_score = score
                best_category = category

        # Get full path from taxonomy
        if best_category:
            paths = self.mapper.get_paths_by_category_name(best_category, text)
            if paths:
                # Use most specific path (already sorted by get_paths_by_category_name)
                return (paths[0], best_score)
                
        # Fallback to default category
        return ("Apparel & Accessories > Clothing", 0.1)

    def _extract_sleeve_length(self, description: str) -> Optional[str]:
        """Extract sleeve length type from product text"""
        # Convert HTML to text
        soup = BeautifulSoup(description, 'html.parser')
        text = f"{soup.get_text(separator=' ')}".lower()
        
        # Try to match using ATTRIBUTE_PATTERNS first
        sleeve_patterns = self.ATTRIBUTE_PATTERNS.get('sleeve-length-type', {})
        for sleeve_type, pattern in sleeve_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"Found sleeve type from pattern: {sleeve_type}")
                return sleeve_type.replace(' Sleeve', '')  # Remove "Sleeve" suffix to match taxonomy values
        
        # If no pattern match, try to infer from measurements
        match = re.search(r"sleeve length.*?(\d+\.?\d*)", text)
        if match:
            length = float(match.group(1))
            logger.debug(f"Found sleeve length measurement: {length} inches")
            
            if length >= 18:
                logger.debug("Inferred Long sleeve from measurement")
                return 'Long'
            elif length >= 15:
                logger.debug("Inferred Three Quarter sleeve from measurement")
                return 'Three Quarter'
            elif length >= 8:
                logger.debug("Inferred Short sleeve from measurement")
                return 'Short'
            
        return None

    def _detect_gender(self, title: str, description: str) -> str:
        """
        Detect target gender from product text.
        Defaults to Female for most clothing types.
        """
        text = f"{title} {description}".lower()
        title_lower = title.lower()
        
        # First check clothing type indicators (highest priority)
        for item in self.FEMININE_CLOTHING:
            if item in title_lower:
                logger.debug(f"Detected feminine clothing type: {item}")
                return 'Female'
            
        # Then check size indicators (second priority)
        if any(size in text for term in ["6/8", "10/12", "14/16", "xs", "s/m"]):
            logger.debug("Found feminine size indicators")
            return 'Female'
        
        # Then check explicit gender indicators
        if any(term in text for term in ['women', 'womens', "women's", 'ladies', 'feminine']):
            logger.debug("Found explicit female gender indicator")
            return 'Female'
        if any(term in text for term in ['men', 'mens', "men's", 'masculine']):
            logger.debug("Found explicit male gender indicator")
            return 'Male'
        if any(term in text for term in ['unisex', 'gender neutral', 'gender-neutral']):
            logger.debug("Found explicit unisex gender indicator")
            return 'Unisex'
            
        # Check masculine clothing only after other checks
        for item in self.MASCULINE_CLOTHING:
            if item in title_lower:
                logger.debug(f"Detected masculine clothing type: {item}")
                return 'Male'
            
        # Default to Female for most clothing
        logger.debug("No gender indicators found, defaulting to Female")
        return 'Female'

    def get_suggested_attributes(self, title: str, description: str = "") -> Dict[str, str]:
        """Extract suggested attributes based on product text"""
        text = f"{title} {description}".lower()
        attributes = {}
        
        # Get category and allowed attributes
        category_path, _ = self.categorize(title, description)
        category_id = self.mapper.get_category_id_from_path(category_path)
        if not category_id:
            return {}
            
        allowed_attrs = self.mapper.get_allowed_attributes(category_id)
        logger.debug(f"Category {category_id} allows attributes: {allowed_attrs}")
        
        # Process each allowed attribute
        for attr_id in allowed_attrs:
            attr_info = self.mapper.get_attribute_info(attr_id)
            if not attr_info:
                continue
            
            attr_handle = attr_info.get('handle')
            logger.debug(f"\nProcessing attribute {attr_handle} ({attr_id})")
            
            # Special handling for different attribute types
            if attr_handle == 'target-gender':
                gender = self._detect_gender(title, description)
                value_id = self.mapper.get_value_id_by_name(attr_id, gender)
                if value_id:
                    attributes[attr_id] = value_id
                    logger.debug(f"Set gender to {gender} ({value_id})")
                
            elif attr_handle == 'fabric':
                # Look for material composition
                material_match = re.search(r'material composition:?\s*(\d{1,3}%\s*)?([a-zA-Z]+)', text)
                if material_match:
                    material = material_match.group(2).strip()
                    logger.debug(f"Found fabric in text: {material}")
                    value_id = self.mapper.get_value_id_by_name(attr_id, material)
                    if value_id:
                        attributes[attr_id] = value_id
                        logger.debug(f"Set fabric to {material} ({value_id})")
                    
            elif attr_handle == 'top-length-type':
                # Check for length indicators
                if any(term in text for term in ['longline', 'long length', 'maxi']):
                    value_id = self.mapper.get_value_id_by_name(attr_id, 'Long')
                    if value_id:
                        attributes[attr_id] = value_id
                        logger.debug(f"Set length type to Long ({value_id})")
                    
            elif attr_handle == 'clothing-features':
                # Check for features
                if 'stretch' in text or 'stretchy' in text:
                    value_id = self.mapper.get_value_id_by_name(attr_id, 'Stretchable')
                    if value_id:
                        attributes[attr_id] = value_id
                        logger.debug(f"Set feature to Stretchable ({value_id})")
                    
            elif attr_handle == 'sleeve-length-type':
                sleeve_length = self._extract_sleeve_length(description)
                if sleeve_length:
                    value_id = self.mapper.get_value_id_by_name(attr_id, sleeve_length)
                    if value_id:
                        attributes[attr_id] = value_id
                        logger.debug(f"Set sleeve length to {sleeve_length} ({value_id})")
        
        logger.debug(f"Final extracted attributes: {attributes}")
        return attributes

def main():
    """Example usage"""
    categorizer = ClothingCategorizer()
    
    # Test cases
    test_products = [
        {
            "title": "Classic Cotton Crew Neck T-Shirt",
            "description": "A comfortable short-sleeve tee made from 100% organic cotton."
        },
        {
            "title": "Slim Fit Dark Wash Jeans",
            "description": "Premium denim pants with a modern slim cut."
        },
        {
            "title": "Floral Summer Maxi Dress",
            "description": "Long flowing dress perfect for warm weather."
        }
    ]
    
    for product in test_products:
        # Get category
        category, confidence = categorizer.categorize(
            product["title"], 
            product["description"]
        )
        
        # Get suggested attributes
        attributes = categorizer.get_suggested_attributes(
            product["title"],
            product["description"]
        )
        
        print(f"\nProduct: {product['title']}")
        print(f"Category: {category}")
        print(f"Confidence: {confidence:.2f}")
        print("Suggested Attributes:")
        for attr_id, value in attributes.items():
            print(f"  {attr_id}: {value}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main() 