from typing import Dict, Optional, Tuple
import logging
from pathlib import Path
from ..utils.taxonomy_mapper import TaxonomyMapper

logger = logging.getLogger(__name__)

class ClothingCategorizer:
    """Specialized categorizer for clothing/apparel products"""
    
    def __init__(self):
        self.taxonomy = TaxonomyMapper()
        
        # Clothing-specific category patterns
        self.category_patterns = {
            'Apparel & Accessories > Clothing > Clothing Tops > Tank Tops': {
                'required': ['tube', 'tank', 'cami'],  # Need any one of these
                'optional': ['sweetheart', 'twisted', 'eyelet', 'feminine', 'neck', 'crop', 'sleeveless'],
                'negative': ['dress', 'pants', 'skirt', 'long sleeve', 'tshirt', 't-shirt', 'blouse', 'gown', 'maxi', 'midi']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Blouses': {
                'required': ['blouse', 'button up', 'button-up', 'button down'],  # More specific to blouses
                'optional': ['eyelet', 'sweetheart', 'twisted', 'ruffle', 'peplum', 'collar', 'feminine', 'dressy', 'neck', 'lace', 'silk'],
                'negative': ['athletic', 'sport', 'hoodie', 'sweatshirt', 'tshirt', 't-shirt', 'tank', 'tube']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > T-Shirts': {
                'required': ['tee', 't-shirt', 'tshirt'],
                'optional': ['crew neck', 'v-neck', 'graphic', 'basic', 'casual'],
                'negative': ['tank', 'dress', 'pants', 'skirt', 'sweetheart']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Sweaters': {
                'required': ['sweater', 'cardigan', 'pullover'],
                'optional': ['knit', 'wool', 'cashmere', 'ribbed', 'cozy'],
                'negative': ['tank', 't-shirt', 'blouse']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Sweatshirts': {
                'required': ['sweatshirt', 'hoodie', 'fleece'],
                'optional': ['pullover', 'zip-up', 'athletic', 'casual'],
                'negative': ['dress', 'blouse', 'tank']
            },
            'Apparel & Accessories > Clothing > Dresses > Casual Dresses': {
                'required': ['dress'],  # Must have 'dress'
                'optional': ['casual', 'comfortable', 'day', 'everyday', 'relaxed', 'linen', 'a-line', 'flared'],
                'negative': ['formal', 'evening', 'gown', 'cocktail', 'wedding']
            },
            'Apparel & Accessories > Clothing > Dresses > Cocktail Dresses': {
                'required': ['dress', 'cocktail'],
                'optional': ['party', 'evening', 'formal', 'elegant', 'fitted', 'special occasion'],
                'negative': ['casual', 'day', 'beach', 'lounge', 't-shirt']
            },
            'Apparel & Accessories > Clothing > Dresses > Formal Dresses': {
                'required': ['dress', 'gown', 'formal'],
                'optional': ['evening', 'elegant', 'special occasion', 'wedding', 'ball', 'prom'],
                'negative': ['casual', 'day', 'beach', 't-shirt']
            },
            'Apparel & Accessories > Clothing > Dresses > Mini Dresses': {
                'required': ['dress', 'mini'],  # Must have both 'dress' AND 'mini'
                'optional': ['short', 'above knee', 'a-line', 'flared', 'skater', 'linen', 'casual'],
                'negative': ['maxi', 'long', 'midi', 'floor length']
            },
            'Apparel & Accessories > Clothing > Dresses > Midi Dresses': {
                'required': ['dress', 'midi'],
                'optional': ['knee length', 'tea length', 'calf length'],
                'negative': ['mini', 'maxi', 'floor length']
            }
        }

        # Add metafield patterns
        self.metafield_patterns = {
            'fabric': {
                'cotton': ['cotton', '100% cotton'],
                'viscose': ['viscose', 'rayon'],
                'polyester': ['polyester', 'poly'],
                'linen': ['linen', 'linen mix', 'linen blend'],
                'wool': ['wool', 'merino'],
                'denim': ['denim', 'jean'],
                'french-terry': ['french terry']
            },
            'neckline': {
                'round': ['round neck', 'crew neck'],
                'v-neck': ['v-neck', 'vneck'],
                'square': ['square neck'],
                'sweetheart': ['sweetheart'],
                'halter': ['halter'],
                'cowl': ['cowl'],
                'turtleneck': ['turtleneck', 'mock neck']
            },
            'sleeve_length_type': {
                'sleeveless': ['sleeveless', 'tank', 'tube'],
                'short': ['short sleeve'],
                'three-quarter': ['3/4 sleeve'],
                'long': ['long sleeve'],
                'cap': ['cap sleeve']
            },
            'clothing_features': {
                'stretchable': ['stretch', 'stretchy', 'spandex', 'elastane']
            },
            'target_gender': {
                'female': ['women', 'womens', 'ladies', 'feminine'],
                'male': ['men', 'mens', 'masculine'],
                'unisex': ['unisex', 'gender neutral']
            },
            'age_group': {
                'adults': ['adult', 'women', 'men', 'ladies'],
                'kids': ['kids', 'children', 'youth', 'junior'],
                'baby': ['baby', 'infant', 'toddler']
            },
            'dress_style': {
                'a-line': ['a-line', 'flared', 'skater', 'ric rac'],
                'fitted': ['fitted', 'bodycon', 'form-fitting'],
                'wrap': ['wrap', 'surplice'],
                'shift': ['shift', 'straight'],
                'sheath': ['sheath']
            },
            'dress_occasion': {
                'casual': ['casual', 'everyday', 'day'],
                'formal': ['formal', 'evening', 'cocktail'],
                'party': ['party', 'club', 'night out'],
                'work': ['work', 'office', 'business']
            },
            'dress_length': {
                'mini': ['mini', 'above knee', 'short'],
                'midi': ['midi', 'knee length', 'tea length'],
                'maxi': ['maxi', 'floor length', 'long']
            }
        }

    def categorize_product(self, title: str, description: str = None) -> Tuple[str, float]:
        """Categorize a product based on its title and description"""
        # Combine title and description for analysis
        text = f"{title} {description}" if description else title
        text = text.lower()
        
        # Standard category paths
        DRESS_CATEGORY = 'Apparel & Accessories > Clothing > Dresses'
        BLOUSE_CATEGORY = 'Apparel & Accessories > Clothing > Clothing Tops > Blouses'
        
        # Check for dress indicators
        dress_indicators = ['dress', 'a-line', 'maxi', 'midi', 'mini']
        if any(indicator in text for indicator in dress_indicators):
            return DRESS_CATEGORY, 0.95
            
        # Check for blouse/top indicators
        top_indicators = ['blouse', 'top', 'shirt', 'tank', 'tube top']
        if any(indicator in text for indicator in top_indicators):
            return BLOUSE_CATEGORY, 0.9
            
        # Default to lower confidence if no strong indicators
        if 'dress' in text:
            return DRESS_CATEGORY, 0.8
        if 'top' in text or 'blouse' in text:
            return BLOUSE_CATEGORY, 0.8
            
        return None, 0.0

    def infer_metafields(self, title: str, description: str, category: str) -> Dict[str, str]:
        """Infer metafields from product details"""
        metafields = {}
        
        # Extract fabric information
        if "RAYON" in description.upper():
            metafields['fabric'] = 'shopify--fabric.rayon'
        if "LINEN" in description.upper():
            metafields['fabric'] = metafields.get('fabric', '') + ', shopify--fabric.linen'
        if "POLYESTER" in description.upper():
            metafields['fabric'] = metafields.get('fabric', '') + ', shopify--fabric.polyester'
        
        # Basic metafields
        metafields['age_group'] = 'shopify--age-group.adults'
        metafields['target_gender'] = 'shopify--target-gender.female'
        
        # Dress-specific metafields
        if 'Dresses' in category:
            if 'A-LINE' in description.upper():
                metafields['dress_style'] = 'shopify--dress-style.a-line'
            if 'CASUAL' in description.upper():
                metafields['dress_occasion'] = 'shopify--dress-occasion.casual'
            if 'MINI' in description.upper():
                metafields['skirt_dress_length_type'] = 'shopify--skirt-dress-length-type.mini'
            if 'SLEEVELESS' in description.upper():
                metafields['sleeve_length_type'] = 'shopify--sleeve-length-type.sleeveless'
        
        # Only add neckline if we can determine it confidently
        if 'SWEETHEART' in description.upper():
            metafields['neckline'] = 'shopify--neckline.sweetheart'
        
        return metafields

    def _determine_category(self, title: str, description: str = '') -> Tuple[str, float, Dict]:
        """Categorize a clothing product"""
        logger.info(f"Categorizing product: {title}")
        
        combined_text = f"{title} {description}".lower()
        logger.debug(f"Combined text: {combined_text}")
        logger.debug(f"Available categories: {list(self.category_patterns.keys())}")
        
        # Add more detailed debug logging for term matching
        for category, patterns in self.category_patterns.items():
            logger.debug(f"\nChecking {category}:")
            logger.debug(f"  Required terms: {patterns['required']}")
            logger.debug(f"  Optional terms: {patterns['optional']}")
            logger.debug(f"  Negative terms: {patterns['negative']}")
            
            # Log actual matches
            required_matches = [t for t in patterns['required'] if t in combined_text]
            optional_matches = [t for t in patterns['optional'] if t in combined_text]
            negative_matches = [t for t in patterns['negative'] if t in combined_text]
            
            logger.debug(f"  Found required: {required_matches}")
            logger.debug(f"  Found optional: {optional_matches}")
            logger.debug(f"  Found negative: {negative_matches}")
        
        # Try each category pattern
        best_match = None
        best_score = 0.0
        best_category = None
        
        for category, patterns in self.category_patterns.items():
            logger.debug(f"\nChecking category: {category}")
            logger.debug(f"Looking for any of these required terms: {patterns['required']}")
            
            # Check required terms - need ANY required term
            required_matches = [t for t in patterns['required'] if t in combined_text]
            if not required_matches:
                logger.debug(f"No required terms found in text: '{combined_text}'")
                continue
                
            logger.debug(f"Found required terms: {required_matches}")
            
            # Calculate match score based on number of matches
            base_score = 0.6
            required_bonus = min(0.2, len(required_matches) * 0.1)
            score = base_score + required_bonus
            logger.debug(f"Score calculation:")
            logger.debug(f"  Base score: {base_score}")
            logger.debug(f"  Required bonus ({len(required_matches)} matches): +{required_bonus}")
            
            # Add optional matches
            optional_matches = [term for term in patterns['optional'] if term in combined_text]
            optional_bonus = min(0.2, len(optional_matches) * 0.05)
            score += optional_bonus
            logger.debug(f"  Optional bonus ({len(optional_matches)} matches): +{optional_bonus}")
            logger.debug(f"  Optional terms found: {optional_matches}")
            
            # Check negative terms - reduce score for each match
            negative_matches = [t for t in patterns['negative'] if t in combined_text]
            negative_penalty = len(negative_matches) * 0.1
            score -= negative_penalty
            logger.debug(f"  Negative penalty ({len(negative_matches)} matches): -{negative_penalty}")
            logger.debug(f"  Negative terms found: {negative_matches}")
            
            logger.debug(f"  Final score: {score}")
            
            if score > best_score:
                best_score = score
                best_category = category
                best_match = {
                    'category': category,
                    'score': score,
                    'matched_required': required_matches,
                    'matched_optional': optional_matches,
                    'negative_matches': negative_matches
                }
                logger.debug(f"New best match: {category} (score: {score})")
        
        if not best_category:
            logger.warning(f"No category matched for text: '{combined_text}'")
            
        # Get category ID from taxonomy mapper
        category_id = self.taxonomy.get_category_id(best_category) if best_category else None
        logger.debug(f"Found category ID: {category_id} for category: {best_category}")
        
        return best_category, best_score, {
            'raw_title': title,
            'error': 'No matching category found' if not best_category else None,
            'confidence': best_score,
            'category_id': category_id,
            'matches': best_match
        }

    def debug_available_categories(self, search_term: str = '') -> None:
        """Show available clothing categories"""
        self.taxonomy.debug_available_categories(search_term) 