import pandas as pd
import logging
from pathlib import Path
from typing import Union, Dict, List, Tuple, Optional
import re
from collections import defaultdict
import yaml
import sys

# Add parent directory to path so we can import from utils
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

from utils.taxonomy_mapper import TaxonomyMapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

class CategoryMatcher:
    """Helper class for sophisticated category pattern matching"""
    def __init__(self):
        # Keywords that strongly indicate specific categories
        self.category_indicators = {
            # Tops
            'Apparel & Accessories > Clothing > Clothing Tops > T-Shirts': {
                'required': ['tee', 't-shirt', 'tshirt'],
                'optional': ['crew neck', 'v-neck', 'graphic', 'basic', 'casual', 'short sleeve'],
                'negative': ['tank', 'dress', 'pants', 'skirt', 'sweater', 'hoodie']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Tank Tops': {
                'required': ['tank', 'tube'],
                'optional': ['ribbed', 'knit', 'cami', 'sleeveless', 'racerback', 'spaghetti strap'],
                'negative': ['dress', 'pants', 'skirt', 'sleeve', 'sweater']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Blouses': {
                'required': ['blouse', 'eyelet', 'sweetheart'],
                'optional': ['button', 'collar', 'sleeveless', 'long sleeve', 'short sleeve', 'feminine', 'dressy'],
                'negative': ['dress', 'pants', 'skirt', 'sweater', 'athletic', 'sport']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Sweaters': {
                'required': ['sweater', 'cardigan', 'pullover', 'knit'],
                'optional': ['wool', 'cashmere', 'button', 'zip', 'cable knit'],
                'negative': ['dress', 'pants', 'skirt', 't-shirt']
            },
            
            # Dresses
            'Apparel & Accessories > Clothing > Dresses > Casual Dresses': {
                'required': ['dress'],
                'optional': ['casual', 'day', 'everyday', 'comfortable', 'relaxed', 't-shirt dress'],
                'negative': ['formal', 'evening', 'gown', 'cocktail']
            },
            'Apparel & Accessories > Clothing > Dresses > Formal Dresses': {
                'required': ['dress'],
                'optional': ['formal', 'evening', 'gown', 'cocktail', 'elegant', 'special occasion'],
                'negative': ['casual', 'everyday', 't-shirt']
            },
            
            # Pants
            'Apparel & Accessories > Clothing > Pants > Wide Leg Pants': {
                'required': ['pants', 'wide leg'],
                'optional': ['flare', 'palazzo', 'loose', 'flowing', 'relaxed', 'baggy'],
                'negative': ['skinny', 'legging', 'tight', 'slim']
            },
            'Apparel & Accessories > Clothing > Pants > Cargo Pants': {
                'required': ['cargo', 'pants'],
                'optional': ['pocket', 'utility', 'military', 'tactical'],
                'negative': ['dress', 'formal', 'legging']
            },
            
            # Outerwear
            'Apparel & Accessories > Clothing > Outerwear > Jackets': {
                'required': ['jacket'],
                'optional': ['zip', 'button', 'bomber', 'denim', 'leather', 'moto'],
                'negative': ['dress', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Outerwear > Blazers': {
                'required': ['blazer'],
                'optional': ['suit', 'formal', 'tailored', 'professional', 'business'],
                'negative': ['casual', 'hoodie', 'sweatshirt']
            },
            
            # One-Pieces
            'Apparel & Accessories > Clothing > One-Pieces > Jumpsuits': {
                'required': ['jumpsuit', 'jumper'],
                'optional': ['full length', 'one piece', 'pantsuit'],
                'negative': ['dress', 'romper', 'short']
            },
            'Apparel & Accessories > Clothing > One-Pieces > Rompers': {
                'required': ['romper', 'playsuit'],
                'optional': ['short', 'summer', 'casual'],
                'negative': ['dress', 'jumpsuit', 'pants']
            },
            
            # Activewear
            'Apparel & Accessories > Clothing > Activewear > Athletic Tops': {
                'required': ['athletic', 'sport', 'workout', 'training'],
                'optional': ['moisture wicking', 'performance', 'gym', 'running'],
                'negative': ['dress', 'casual', 'formal']
            },
            'Apparel & Accessories > Clothing > Activewear > Athletic Pants': {
                'required': ['athletic', 'sport', 'workout', 'training'],
                'optional': ['moisture wicking', 'performance', 'gym', 'running'],
                'negative': ['casual', 'formal', 'dress']
            },
            'Apparel & Accessories > Clothing > Pants > French Terry Pants': {
                'required': ['french terry', 'pants'],
                'optional': ['jogger', 'lounge', 'comfortable', 'casual'],
                'negative': ['dress', 'top', 'skirt']
            },
            'Apparel & Accessories > Clothing > Dresses > Tiered Dresses': {
                'required': ['dress', 'tiered'],
                'optional': ['flutter sleeve', 'ruffle', 'layered', 'floral', 'tie waist'],
                'negative': ['top', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Dresses > Flutter Sleeve Dresses': {
                'required': ['dress', 'flutter sleeve'],
                'optional': ['tiered', 'ruffle', 'floral', 'tie waist'],
                'negative': ['top', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Dresses > Floral Dresses': {
                'required': ['dress', 'floral'],
                'optional': ['tiered', 'ruffle', 'layered', 'floral', 'tie waist'],
                'negative': ['top', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Ribbed Tops': {
                'required': ['ribbed'],
                'optional': ['tank', 'knit', 'fitted', 'stretch', 'basic'],
                'negative': ['dress', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Crop Tops': {
                'required': ['crop', 'cropped'],
                'optional': ['top', 'blouse', 'shirt', 'sleeveless', 'collar', 'button'],
                'negative': ['dress', 'pants', 'skirt', 'sweater']
            }
        }
        
        # Style indicators that help determine subcategories
        self.style_indicators = {
            'casual': ['casual', 'relaxed', 'everyday', 'basic', 'lounge', 'comfortable'],
            'formal': ['formal', 'elegant', 'dressy', 'sophisticated', 'professional', 'business'],
            'athletic': ['athletic', 'sport', 'workout', 'active', 'performance', 'gym', 'training'],
            'wide_leg': ['wide leg', 'flare', 'palazzo', 'baggy', 'loose fit', 'flowing'],
            'fitted': ['fitted', 'slim', 'skinny', 'bodycon', 'form-fitting', 'tight'],
            'vintage': ['vintage', 'retro', 'classic', 'traditional'],
            'modern': ['modern', 'contemporary', 'trendy', 'fashion-forward'],
            'bohemian': ['boho', 'bohemian', 'hippie', 'free-spirited'],
            'preppy': ['preppy', 'collegiate', 'academic', 'classic'],
            'babydoll': ['babydoll', 'baby doll', 'tiered', 'peplum'],
            'layered': ['tiered', 'layered', 'ruffle tier', 'handkerchief hem', 'bubble hem'],
            'workwear': ['shacket', 'utility', 'cargo', 'workwear'],
            'bodycon': ['bodysuit', 'form-fitting', 'fitted', 'stretch']
        }
        
        # Material indicators that help determine category and style
        self.material_indicators = {
            'casual': ['cotton', 'jersey', 'french terry', 'denim', 'linen', 'chambray'],
            'formal': ['silk', 'satin', 'chiffon', 'velvet', 'taffeta', 'organza'],
            'athletic': ['spandex', 'lycra', 'moisture-wicking', 'performance', 'mesh'],
            'outerwear': ['wool', 'leather', 'down', 'fleece', 'sherpa', 'suede'],
            'summer': ['linen', 'cotton', 'rayon', 'chambray'],
            'winter': ['wool', 'cashmere', 'fleece', 'down', 'velvet'],
            'structured': ['denim', 'twill', 'canvas', 'leather'],
            'flowing': ['chiffon', 'silk', 'rayon', 'georgette']
        }

        # Add pattern modifiers for better matching
        self.pattern_modifiers = {
            'sleeve_length': ['sleeveless', 'short sleeve', 'long sleeve', '3/4 sleeve'],
            'neckline': ['crew neck', 'v-neck', 'scoop neck', 'turtleneck', 'mock neck'],
            'length': ['mini', 'midi', 'maxi', 'knee length', 'ankle length'],
            'fit': ['relaxed fit', 'slim fit', 'regular fit', 'oversized', 'fitted'],
            'closure': ['button-up', 'zip-up', 'pullover', 'wrap', 'tie']
        }

        # Add new category patterns
        self.category_indicators.update({
            'Apparel & Accessories > Clothing > Outerwear > Shackets': {
                'required': ['shacket'],
                'optional': ['button up', 'chest pocket', 'oversized', 'utility'],
                'negative': ['dress', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Bodysuits': {
                'required': ['bodysuit'],
                'optional': ['long sleeve', 'short sleeve', 'stretch', 'fitted'],
                'negative': ['dress', 'jacket', 'coat']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Peplum Tops': {
                'required': ['peplum'],
                'optional': ['blouse', 'top', 'ruffle', 'waist'],
                'negative': ['dress', 'skirt', 'pants']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Babydoll Tops': {
                'required': ['babydoll'],
                'optional': ['top', 'blouse', 'tiered', 'ruffle'],
                'negative': ['dress', 'skirt', 'pants']
            },
            # Sets and Coordinates
            'Apparel & Accessories > Clothing > Outfit Sets > Top & Shorts Sets': {
                'required': ['set', 'shorts'],
                'optional': ['top', 'crop', 'matching', 'coordinate', 'two piece'],
                'negative': ['dress', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Outfit Sets > Top & Skirt Sets': {
                'required': ['set', 'skirt'],
                'optional': ['top', 'crop', 'matching', 'coordinate', 'two piece'],
                'negative': ['dress', 'pants', 'shorts']
            },
            'Apparel & Accessories > Clothing > Outfit Sets > Top & Pants Sets': {
                'required': ['set', 'pants'],
                'optional': ['top', 'crop', 'matching', 'coordinate', 'two piece'],
                'negative': ['dress', 'shorts', 'skirt']
            },

            # Specialized Tops
            'Apparel & Accessories > Clothing > Clothing Tops > Cami Tops': {
                'required': ['cami'],
                'optional': ['top', 'spaghetti strap', 'sleeveless', 'ribbed'],
                'negative': ['dress', 'pants', 'jacket']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Gauze Tops': {
                'required': ['gauze'],
                'optional': ['top', 'blouse', 'shirt', 'cotton', 'lightweight'],
                'negative': ['dress', 'pants', 'jacket']
            },

            # Specialized Dresses
            'Apparel & Accessories > Clothing > Dresses > Babydoll Dresses': {
                'required': ['babydoll', 'dress'],
                'optional': ['tiered', 'ruffle', 'flowy', 'mini'],
                'negative': ['top', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Dresses > Shirt Dresses': {
                'required': ['shirt dress', 'button down dress'],
                'optional': ['collar', 'button', 'midi', 'mini'],
                'negative': ['top', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Dresses > Tiered Dresses': {
                'required': ['tiered', 'dress'],
                'optional': ['ruffle', 'layered', 'midi', 'maxi'],
                'negative': ['top', 'pants', 'skirt']
            },

            # Specialized Bottoms
            'Apparel & Accessories > Clothing > Shorts > Skorts': {
                'required': ['skort'],
                'optional': ['pleated', 'mini', 'athletic', 'tennis'],
                'negative': ['dress', 'pants', 'skirt']
            },

            # Specialized Outerwear
            'Apparel & Accessories > Clothing > Outerwear > Sherpa Jackets': {
                'required': ['sherpa'],
                'optional': ['jacket', 'coat', 'zip up', 'button up', 'fuzzy'],
                'negative': ['dress', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Outerwear > Quilted Jackets': {
                'required': ['quilted'],
                'optional': ['jacket', 'coat', 'zip up', 'puffer', 'padded'],
                'negative': ['dress', 'pants', 'skirt']
            }
        })

        # Add garment detail modifiers
        self.garment_modifiers = {
            'cut': ['tiered', 'layered', 'peplum', 'babydoll', 'handkerchief', 'bubble'],
            'length': ['cropped', 'longline', 'oversized', 'mini', 'midi', 'maxi'],
            'detail': ['ruffle', 'smocked', 'pleated', 'gathered', 'twisted', 'knotted'],
            'neckline': ['v-neck', 'scoop', 'square neck', 'sweetheart', 'halter', 'mock neck'],
            'sleeve': ['puff sleeve', 'balloon sleeve', 'cap sleeve', 'flutter sleeve', 'dolman', 'raglan'],
            'collar_type': ['johnny collar', 'peter pan collar', 'mandarin collar', 'notched collar', 'spread collar'],
            'sleeve_type': ['sleeveless', 'cap sleeve', 'short sleeve', 'long sleeve', '3/4 sleeve']
        }

        # Add new pattern modifiers for common details
        self.pattern_modifiers.update({
            'fabric_treatment': ['mineral wash', 'acid wash', 'tie dye', 'distressed', 'raw hem'],
            'fabric_texture': ['ribbed', 'waffle', 'french terry', 'gauze', 'sherpa', 'quilted'],
            'embellishment': ['embroidered', 'crochet', 'lace', 'eyelet', 'smocked'],
            'waist': ['elastic waist', 'drawstring', 'high waist', 'paperbag'],
            'hem': ['raw hem', 'frayed', 'scalloped', 'handkerchief', 'bubble']
        })

        # Add new style indicators
        self.style_indicators.update({
            'lounge': ['french terry', 'comfortable', 'relaxed', 'elastic waist'],
            'resort': ['gauze', 'linen', 'eyelet', 'crochet', 'vacation'],
            'romantic': ['ruffle', 'tiered', 'babydoll', 'smocked', 'eyelet'],
            'minimalist': ['basic', 'classic', 'simple', 'essential', 'clean']
        })

        # Add more specialized category patterns
        self.category_indicators.update({
            # Specialized Tops Continued
            'Apparel & Accessories > Clothing > Clothing Tops > Waffle Knit Tops': {
                'required': ['waffle', 'knit'],
                'optional': ['top', 'thermal', 'henley', 'textured'],
                'negative': ['dress', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Thermal Tops': {
                'required': ['thermal'],
                'optional': ['top', 'waffle', 'henley', 'long sleeve'],
                'negative': ['dress', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Clothing Tops > Bralette Tops': {
                'required': ['bralette'],
                'optional': ['crop', 'smocked', 'ribbed', 'knit'],
                'negative': ['dress', 'pants', 'skirt']
            },

            # Specialized Dresses Continued
            'Apparel & Accessories > Clothing > Dresses > Smocked Dresses': {
                'required': ['smocked', 'dress'],
                'optional': ['elastic', 'ruched', 'fitted', 'bodice'],
                'negative': ['top', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Dresses > Tube Dresses': {
                'required': ['tube', 'dress'],
                'optional': ['strapless', 'bodycon', 'fitted'],
                'negative': ['top', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Dresses > Poplin Dresses': {
                'required': ['poplin', 'dress'],
                'optional': ['cotton', 'woven', 'button', 'collar'],
                'negative': ['top', 'pants', 'skirt']
            },

            # Rompers and Jumpsuits
            'Apparel & Accessories > Clothing > One-Pieces > Overall Rompers': {
                'required': ['overall', 'romper'],
                'optional': ['denim', 'bib', 'pocket', 'short'],
                'negative': ['dress', 'pants', 'long']
            },
            'Apparel & Accessories > Clothing > One-Pieces > Denim Jumpsuits': {
                'required': ['denim', 'jumpsuit'],
                'optional': ['overall', 'button', 'long'],
                'negative': ['dress', 'romper', 'short']
            },

            # Specialized Bottoms Continued
            'Apparel & Accessories > Clothing > Pants > Gauze Pants': {
                'required': ['gauze', 'pants'],
                'optional': ['wide leg', 'elastic', 'lightweight'],
                'negative': ['dress', 'top', 'skirt']
            },
            'Apparel & Accessories > Clothing > Pants > Twill Pants': {
                'required': ['twill', 'pants'],
                'optional': ['woven', 'structured', 'cotton'],
                'negative': ['dress', 'top', 'skirt']
            },

            # Cover Ups and Kimonos
            'Apparel & Accessories > Clothing > Outerwear > Kimono Cover Ups': {
                'required': ['kimono'],
                'optional': ['cover up', 'open front', 'sleeve', 'fringe'],
                'negative': ['dress', 'pants', 'skirt']
            },
            'Apparel & Accessories > Clothing > Outerwear > Crochet Cover Ups': {
                'required': ['crochet', 'cover up'],
                'optional': ['knit', 'open', 'beach', 'swim'],
                'negative': ['dress', 'pants', 'skirt']
            },

            # Specialized Sets
            'Apparel & Accessories > Clothing > Outfit Sets > Lounge Sets': {
                'required': ['set', 'lounge'],
                'optional': ['matching', 'comfortable', 'knit', 'coordinated'],
                'negative': ['formal', 'dress', 'blazer']
            },
            'Apparel & Accessories > Clothing > Outfit Sets > Sweater Sets': {
                'required': ['set', 'sweater'],
                'optional': ['knit', 'matching', 'coordinated', 'cardigan'],
                'negative': ['dress', 'casual', 'cotton']
            }
        })

        # Add new fabric patterns
        self.pattern_modifiers.update({
            'special_fabrics': [
                'mineral wash', 'acid wash', 'tie dye', 
                'french terry', 'waffle knit', 'thermal',
                'poplin', 'gauze', 'twill', 'chambray'
            ],
            'textures': [
                'crinkle', 'bubble', 'popcorn', 'boucle',
                'jacquard', 'pointelle', 'ribbed', 'textured'
            ],
            'embellishments': [
                'crochet', 'eyelet', 'lace', 'embroidered',
                'applique', 'studded', 'beaded', 'sequin'
            ]
        })

        # Add brand-specific style indicators
        self.brand_style_indicators = {
            'MABLE': ['feminine', 'romantic', 'preppy'],
            'Mittoshop': ['casual', 'comfortable', 'everyday'],
            'HYFVE': ['trendy', 'youthful', 'contemporary'],
            'Umgee': ['bohemian', 'relaxed', 'feminine'],
            'Aemi + Co': ['modern', 'minimal', 'essential'],
            'BiBi': ['vintage', 'workwear', 'utility']
        }

        # Add detailed construction patterns
        self.garment_modifiers.update({
            'construction_details': [
                'pintuck', 'exposed seam', 'raw hem', 'handkerchief hem',
                'bubble hem', 'lettuce hem', 'scalloped', 'ricrac trim',
                'crisscross', 'twisted', 'openwork', 'babydoll'
            ],
            'neckline_details': [
                'johnny collar', 'notched', 'square neck', 'sweetheart',
                'plunge', 'halter', 'mock neck', 'collared'
            ],
            'sleeve_details': [
                'raglan', 'dolman', 'flutter', 'puff', 'flounce',
                'cap sleeve', 'bell sleeve', 'rolled sleeve'
            ]
        })

        # Add fabric textures and treatments
        self.pattern_modifiers.update({
            'textures': [
                'waffle knit', 'thermal', 'ribbed', 'pointelle',
                'eyelet', 'crochet', 'lace', 'velvet', 'corduroy',
                'mineral wash', 'acid wash'
            ],
            'treatments': [
                'smocked', 'ruched', 'pleated', 'pintucked',
                'distressed', 'washed', 'textured'
            ]
        })

        # Add specific garment types
        self.category_types = {
            'sets': [
                'lounge set', 'sweater set', 'crop top set',
                'short set', 'pant set', 'matching set'
            ],
            'dresses': [
                'tube dress', 'cami dress', 'shirt dress',
                'babydoll dress', 'tiered dress', 'midi dress'
            ],
            'tops': [
                'shacket', 'bodysuit', 'crop top', 'tube top',
                'bralette', 'cami', 'tank'
            ]
        }

        # Add fit and silhouette modifiers
        self.fit_modifiers = {
            'silhouette': [
                'oversized', 'fitted', 'relaxed', 'slim',
                'wide leg', 'flare', 'straight', 'skinny'
            ],
            'length': [
                'cropped', 'midi', 'mini', 'maxi',
                'high-low', 'ankle length'
            ],
            'rise': [
                'high rise', 'mid rise', 'low rise',
                'tummy control'
            ]
        }

        # Add size and fit indicators
        self.size_fit_indicators = {
            'regular_sizing': [
                r'S:.*M:.*L:', r'Small.*Medium.*Large',
                r'\d{2}"\s*[xX]\s*\d{2}"', r'Size \d+'
            ],
            'plus_sizing': [
                r'1XL|2XL|3XL', r'Plus Size', r'Curvy',
                r'Size \d{2}\+', r'Size \d{2}W'
            ],
            'measurements': {
                'bust': [r'bust:?\s*\d+', r'chest:?\s*\d+', r'B:?\s*\d+'],
                'waist': [r'waist:?\s*\d+', r'W:?\s*\d+'],
                'hip': [r'hip:?\s*\d+', r'H:?\s*\d+'],
                'inseam': [r'inseam:?\s*\d+', r'IL:?\s*\d+']
            }
        }

        # Add fit descriptors that help identify garment types
        self.fit_descriptors = {
            'tops': {
                'fitted': ['slim fit', 'form fitting', 'bodycon'],
                'loose': ['oversized', 'relaxed fit', 'boyfriend fit'],
                'cropped': ['crop', 'cropped length', 'above waist']
            },
            'bottoms': {
                'rise': ['high rise', 'mid rise', 'low rise'],
                'leg': ['skinny', 'straight leg', 'wide leg', 'flare'],
                'length': ['ankle length', 'full length', 'cropped', 'capri']
            },
            'dresses': {
                'fit': ['bodycon', 'a-line', 'shift', 'wrap'],
                'length': ['mini', 'midi', 'maxi', 'knee length'],
                'waist': ['empire waist', 'drop waist', 'natural waist']
            }
        }

        # Add fabric patterns
        self.fabric_patterns = {
            'natural': [
                'cotton', 'linen', 'silk', 'wool', 'cashmere', 
                'hemp', 'bamboo', 'modal', 'tencel'
            ],
            'synthetic': [
                'polyester', 'nylon', 'spandex', 'lycra', 'acrylic',
                'rayon', 'viscose', 'elastane'
            ],
            'blends': [
                'cotton blend', 'poly blend', 'wool blend',
                'cotton/poly', 'cotton/spandex'
            ],
            'specialty': [
                'velvet', 'chiffon', 'satin', 'lace', 'mesh',
                'denim', 'corduroy', 'leather', 'suede'
            ],
            'construction': [
                'ribbed', 'knit', 'waffle', 'thermal', 'jersey',
                'pointelle', 'cable knit', 'french terry'
            ]
        }

    def _score_fabric_matches(self, text: str) -> float:
        """Score text based on fabric pattern matches"""
        text = text.lower()
        score = 0.0
        detected_fabrics = []
        
        # Check for percentage patterns
        percentage_patterns = [
            r'(\d+)%\s*(cotton|polyester|rayon|spandex|lycra|elastane)',
            r'(cotton|polyester|rayon|spandex|lycra|elastane)\s*(\d+)%'
        ]
        
        for pattern in percentage_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                fabric = match.group(1) if match.group(1).isalpha() else match.group(2)
                detected_fabrics.append(fabric.lower())
                score += 0.3  # Higher score for specific percentage matches
        
        # Check each fabric category
        for category, fabrics in self.fabric_patterns.items():
            for fabric in fabrics:
                if fabric in text and fabric not in detected_fabrics:
                    detected_fabrics.append(fabric)
                    score += 0.2  # Add points for each fabric match
                    
                    # Add bonus for specific fabric details
                    if any(detail in text for detail in [
                        'blend', 'weight', '%', 'ounce', 'gsm',
                        'lightweight', 'heavyweight', 'medium weight'
                    ]):
                        score += 0.1
        
        # Debug logging
        if detected_fabrics:
            logger.debug(f"Detected fabrics: {detected_fabrics}")
        
        return min(1.0, score)  # Cap at 1.0

    def _score_detail_matches(self, text: str) -> float:
        """Score text based on garment detail matches"""
        text = text.lower()
        score = 0.0
        detected_details = []
        
        # Check construction details
        for category, details in self.garment_modifiers.items():
            for detail in details:
                if detail.lower() in text:
                    detected_details.append(detail)
                    score += 0.15
                    break  # Only count one match per category
        
        # Check fit descriptors
        for category, descriptors in self.fit_descriptors.items():
            for fit_type, patterns in descriptors.items():
                if any(pattern in text for pattern in patterns):
                    detected_details.append(fit_type)
                    score += 0.15
                    break
        
        # Special check for sleeveless
        if 'sleeveless' in text:
            detected_details.append('sleeveless')
            score += 0.2  # Higher score for specific construction detail
        
        # Debug logging
        if detected_details:
            logger.debug(f"Detected details: {detected_details}")
        
        return min(1.0, score)

    def score_category_match(self, text: str, category_patterns: Dict, brand: Optional[str] = None) -> float:
        """Enhanced scoring system that considers all patterns and brand context"""
        text = text.lower()
        score = 0.0
        
        # Check required keywords with fuzzy matching
        required_found = any(
            any(req_word in word for word in text.split())
            for req_word in category_patterns['required']
        )
        if not required_found:
            return 0.0
            
        # Check negative keywords
        if any(keyword in text for keyword in category_patterns['negative']):
            return 0.0
        
        # Base score for required match
        score = 0.6
        
        # Add points for optional keywords with weighted scoring
        optional_matches = sum(
            0.2 if keyword in text else
            0.1 if any(kw_part in word for word in text.split() for kw_part in keyword.split())
            else 0.0
            for keyword in category_patterns['optional']
        )
        score += min(0.3, optional_matches)  # Cap optional bonus at 0.3
        
        # Add fit descriptor bonus
        fit_score = self._score_fit_descriptors(text, category_patterns)
        score += fit_score * 0.2  # Max 0.2 for fit matches
        
        # Add size pattern bonus
        size_score = self._score_size_patterns(text)
        score += size_score * 0.1  # Max 0.1 for size matches
        
        return min(1.0, score)

    def _score_fit_descriptors(self, text: str, category_patterns: Dict) -> float:
        """Score text based on fit descriptors for the category type"""
        score = 0.0
        category_type = self._get_category_type(category_patterns)
        
        if category_type in self.fit_descriptors:
            descriptors = self.fit_descriptors[category_type]
            for fit_type, patterns in descriptors.items():
                if any(pattern in text for pattern in patterns):
                    score += 0.3
        
        return min(1.0, score)

    def _score_size_patterns(self, text: str) -> float:
        """Score text based on size and measurement patterns"""
        score = 0.0
        
        # Check regular sizing patterns
        for pattern in self.size_fit_indicators['regular_sizing']:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.2
                break
            
        # Check plus sizing patterns
        for pattern in self.size_fit_indicators['plus_sizing']:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.2
                break
            
        # Check measurement patterns
        for measure_type, patterns in self.size_fit_indicators['measurements'].items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 0.15
                    break
        
        return min(1.0, score)

    def _get_category_type(self, category_patterns: Dict) -> str:
        """Determine the general category type from the patterns"""
        category_keywords = {
            'tops': ['shirt', 'blouse', 'top', 'tee'],
            'bottoms': ['pants', 'shorts', 'skirt'],
            'dresses': ['dress', 'gown']
        }
        
        for cat_type, keywords in category_keywords.items():
            if any(word in ' '.join(category_patterns['required']) for word in keywords):
                return cat_type
        
        return 'other'

    def get_style_indicators(self, text: str) -> Dict[str, float]:
        """Get style scores from text"""
        text = text.lower()
        scores = defaultdict(float)
        
        for style, indicators in self.style_indicators.items():
            matches = sum(indicator in text for indicator in indicators)
            if matches:
                scores[style] = min(1.0, matches * 0.3)
                
        return dict(scores)

    def get_material_indicators(self, text: str) -> Dict[str, float]:
        """Get material type scores from text"""
        text = text.lower()
        scores = defaultdict(float)
        
        for style, materials in self.material_indicators.items():
            matches = sum(material in text for material in materials)
            if matches:
                scores[style] = min(1.0, matches * 0.3)
                
        return dict(scores)

    def infer_category_from_text(self, title: str, description: Optional[str] = None) -> Tuple[str, float, Dict[str, float]]:
        """Enhanced category inference with detailed scoring breakdown"""
        combined_text = (title + ' ' + (description or '')).lower()
        
        # Check for dressy/feminine features
        dressy_features = ['eyelet', 'sweetheart', 'feminine', 'sophisticated', 'romance', 'chic']
        is_dressy = any(feature in combined_text for feature in dressy_features)
        
        # Check for tube/tank features
        tube_features = ['tube', 'tank', 'sleeveless', 'strapless']
        is_tube = any(feature in combined_text for feature in tube_features)
        
        # Base scores
        base_score = 1.0
        fabric_score = 0.8 if any(mat in combined_text for mat in ['cotton', 'viscose', 'spandex']) else 0.6
        detail_score = 0.9 if any(det in combined_text for det in ['eyelet', 'twisted', 'sweetheart']) else 0.7
        style_score = 0.9 if is_dressy else 0.7
        
        # If it's a top
        if 'top' in combined_text:
            category = "Apparel & Accessories > Clothing > Clothing Tops"
            
            if is_tube:
                if is_dressy:
                    category += " > Blouses"
                    logger.info("Categorized as Blouse due to dressy features")
                else:
                    category += " > Tank Tops"
                    logger.info("Categorized as Tank Top")
            elif is_dressy:
                category += " > Blouses"
                logger.info("Categorized as Blouse due to dressy features")
            
            confidence = min(1.0, (base_score + fabric_score + detail_score + style_score) / 4)
            
            return category, confidence, {
                'base_score': base_score,
                'fabric_score': fabric_score,
                'detail_score': detail_score,
                'style_score': style_score,
                'final_score': confidence
            }
        
        return None, 0.0, {
            'error': 'No matching category found',
            'base_score': 0.0,
            'fabric_score': 0.0,
            'detail_score': 0.0,
            'style_score': 0.0,
            'final_score': 0.0
        }

class CategoryNormalizer:
    """Normalizes product categories to match Shopify's taxonomy"""
    
    def __init__(self):
        self.taxonomy_mapper = TaxonomyMapper()
        self.matcher = CategoryMatcher()
        self.category_stats = defaultdict(int)
        self.unrecognized_categories = defaultdict(int)

    def normalize_category(self, title: str, description: str = '') -> Tuple[str, float, Dict]:
        """Normalize product category using title and description"""
        logger.debug(f"Attempting to normalize category for: {title}")
        
        # Get initial category inference
        inferred_category, confidence, scores = self.matcher.infer_category_from_text(
            title, 
            description=description
        )
        
        if inferred_category:
            logger.info(f"Inferred category: {inferred_category}")
            
            # Try to find standard category
            standard_category = self.taxonomy_mapper.get_standard_category(inferred_category)
            if standard_category:
                category_id = self.taxonomy_mapper.get_category_id(standard_category)
                if category_id:
                    logger.info(f"Found matching category: {standard_category}")
                    self.category_stats[standard_category] += 1
                    return standard_category, confidence * 0.9, {
                        'raw_category': title,
                        'confidence': confidence * 0.9,
                        'category_id': category_id,
                        'inferred_category': inferred_category,
                        **scores
                    }
            else:
                logger.warning(f"Could not find standard category for: {inferred_category}")
        
        # No match found
        self.unrecognized_categories[title] += 1
        return None, 0.0, {
            'raw_category': title,
            'confidence': 0.0,
            'error': 'No matching category found'
        }

def process_csv(input_data: Union[str, pd.DataFrame], output_path: str = None) -> Tuple[pd.DataFrame, Dict]:
    """Process Matrixify CSV and normalize categories"""
    # Load data
    if isinstance(input_data, str):
        df = pd.read_csv(input_data)
    else:
        df = input_data.copy()
    
    logger.info("Processing category normalization")
    
    # Initialize normalizer
    normalizer = CategoryNormalizer()
    
    # Track changes for reporting
    changes = []
    
    # Process unique products
    unique_products = df.drop_duplicates('Handle')[['Handle', 'Title', 'Category']]
    
    for _, row in unique_products.iterrows():
        handle = row['Handle']
        title = row['Title']
        original_category = row['Category']
        
        # Normalize category
        normalized_category, confidence, scores = normalizer.normalize_category(
            title, 
            description=original_category if original_category else None
        )
        
        if normalized_category and normalized_category != original_category:
            # Update all variants for this product
            mask = df['Handle'] == handle
            
            # Get category ID from taxonomy mapper
            category_id = scores.get('category_id')
            
            # Update category fields
            df.loc[mask, 'Category'] = normalized_category
            if category_id:
                df.loc[mask, 'Category: ID'] = category_id
            
            changes.append({
                'Handle': handle,
                'Title': title,
                'Old Category': original_category or 'Not Set',
                'New Category': normalized_category,
                'Confidence': confidence,
                'Category ID': category_id,
                'Change Type': 'Inferred' if not original_category else 'Normalized'
            })
    
    # Ensure Command field is set to MERGE
    if 'Command' in df.columns:
        df['Command'] = 'MERGE'
    
    # Save reports
    if output_path:
        report_dir = Path(output_path).parent / 'reports'
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # Save changes report
        if changes:
            changes_df = pd.DataFrame(changes)
            changes_path = report_dir / 'category_normalization_changes.csv'
            changes_df.to_csv(changes_path, index=False)
            logger.info(f"Saved changes report to {changes_path}")
    
        # Save category statistics
        stats_df = pd.DataFrame([
            {'Category': cat, 'Count': count} 
            for cat, count in normalizer.category_stats.items()
        ])
        stats_df.to_csv(report_dir / 'category_statistics.csv', index=False)
        logger.info(f"Saved category statistics to {report_dir / 'category_statistics.csv'}")
    
    # Save normalized CSV
    if output_path:
        df.to_csv(output_path, index=False)
        logger.info(f"Saved normalized CSV to {output_path}")
    
    return df, {
        'changes': changes,
        'unrecognized': dict(normalizer.unrecognized_categories),
        'category_stats': normalizer.category_stats
    }

def get_category_id(category_path: str) -> str:
    """Map category path to Shopify taxonomy ID"""
    # This is a placeholder - you'll need to implement the actual mapping
    category_id_map = {
        'Apparel & Accessories > Clothing > Clothing Tops': 'aa-1-13',
        'Apparel & Accessories > Clothing > Outfit Sets': 'aa-1-14',
        'Apparel & Accessories > Clothing > One-Pieces': 'aa-1-15',
        'Apparel & Accessories > Clothing > Outerwear': 'aa-1-16',
        # Add more mappings as needed
    }
    return category_id_map.get(category_path, '') 

def main():
    """Load and normalize category mappings"""
    taxonomy = TaxonomyMapper()
    
    # Test some lookups
    test_categories = [
        'Apparel & Accessories > Clothing > Dresses > Mini Dresses',
        'Apparel & Accessories > Clothing > Clothing Tops > Tank Tops',
        'Apparel & Accessories > Clothing > Dresses > Casual Dresses'
    ]
    
    for category in test_categories:
        category_id = taxonomy.get_category_id(category)
        print(f"\nCategory: {category}")
        print(f"ID: {category_id}") 