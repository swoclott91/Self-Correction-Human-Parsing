import re
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
from pathlib import Path
from .taxonomy_mapper import TaxonomyMapper
from bs4 import BeautifulSoup
from .category_paths import CATEGORY_PATHS
from .clothing_categorizer_patterns import ATTRIBUTE_PATTERNS

logger = logging.getLogger(__name__)

class ClothingCategorizer:
    """Categorizes clothing products into Shopify taxonomy paths"""
    
    # Simplified category keywords - just focus on identifying the category
    CATEGORY_KEYWORDS = {
        "One-Pieces": ["overall", "overalls", "dungarees", "bib pants", "bib overalls", "jumpsuit", "coveralls"],
        # Tops
        "Cardigans": [
            "cardigan", "open front", "button front sweater", "longline cardigan", 
            "open cardigan", "duster cardigan", "button up cardigan", "button down cardigan",
            "button up sweater", "button front", "open front sweater", "open front long",
            "longline open", "duster style"
        ],
        "T-Shirts": [
            "tee", "t-shirt", "t shirt", "tshirt", "crew neck tee",
            "short sleeve shirt", "graphic tee", "basic tee"
        ],
        "Sweaters": [
            "sweater", "pullover", "jumper", "knit top", "knit sweater", 
            "sweatshirt", "hoodie", "crop sweater", "sweater top",
            "long sleeve sweater", "sleeve crop sweater"
        ],
        "Tops": [
            "top", "shirt", "blouse", "tank", "cami", "tube top", 
            "crop top", "tank top", "sleeveless top", "halter top", "tunic",
            "button up top", "button down top", "strapless top",
            "sweetheart neck top", "twisted top", "bandeau"
        ],
        
        # Bottoms
        "Pants": [
            "pants", "trousers", "slacks", "leggings", "joggers", 
            "cargo pants", "wide leg", "palazzo", "chinos", "jeans",
            "jeggings"
        ],
        "Shorts": [
            "shorts", "bermuda", "cargo shorts", "athletic shorts", 
            "bike shorts", "board shorts", "chino shorts", "denim shorts",
            "jegging shorts", "jogger shorts", "legging shorts"
        ],
        "Skirts": [
            "skirt", "maxi skirt", "midi skirt", "mini skirt", 
            "pleated skirt", "a-line skirt", "pencil skirt",
            "circle skirt", "wrap skirt"
        ],
        
        # One-Piece
        "Dresses": [
            "dress", "maxi", "midi", "mini dress", "bodycon", "a-line",
            "shift dress", "wrap dress", "cami dress", "babydoll", 
            "slip dress", "sweater dress", "shirt dress"
        ],
        "Jumpsuits": [
            "jumpsuit", "romper", "playsuit", "overalls", "dungarees",
            "boiler suit", "coverall"
        ],
        
        # Outerwear
        "Coats": [
            "coat", "jacket", "blazer", "parka", "peacoat", "trench coat",
            "overcoat", "raincoat", "windbreaker", "bomber jacket",
            "denim jacket", "leather jacket"
        ],
        
        # Activewear
        "Activewear": [
            "workout", "athletic", "sport", "gym", "yoga", "running",
            "training", "fitness", "performance"
        ],
        
        # Swimwear
        "Swimwear": [
            "swimsuit", "bikini", "tankini", "swim", "bathing suit",
            "boardshorts", "rash guard", "cover up"
        ],
        
        # Sleepwear
        "Sleepwear": [
            "pajama", "pyjama", "nightgown", "robe", "loungewear",
            "sleep shirt", "nightshirt", "sleeping"
        ],
        
        # Underwear
        "Lingerie": [
            "bra", "panty", "underwear", "lingerie", "shapewear",
            "bodysuit", "slip", "camisole", "corset"
        ],
        
        # Traditional & Ceremonial
        "Traditional": [
            "kimono", "sari", "lehenga", "traditional", "ceremonial",
            "cultural", "ethnic", "heritage"
        ],

        # Uniforms & Workwear
        "Uniforms": [
            "uniform", "scrubs", "workwear", "contractor", "coverall",
            "flight suit", "military", "school uniform", "security",
            "white coat", "chef coat", "lab coat"
        ],

        # Wedding & Bridal
        "Wedding": [
            "wedding", "bridal", "bride", "bridesmaid", "flower girl",
            "matrimonial", "wedding gown", "bridal party"
        ],

        # Accessories
        "Hair Accessories": [
            "hair band", "scrunchie", "hair clip", "bobby pin", "hair tie",
            "headband", "hair bow", "barrette", "hair extension", "wig",
            "hair net", "tiara", "hair pin", "ponytail holder"
        ],
        "Headwear": [
            "hat", "cap", "beanie", "beret", "fedora", "baseball cap",
            "sun hat", "bucket hat", "visor", "snapback", "winter hat",
            "cowboy hat", "trucker hat"
        ],
        "Neckwear": [
            "scarf", "necktie", "bow tie", "bandana", "neck gaiter",
            "shawl", "cravat", "ascot"
        ],
        "Belts & Suspenders": [
            "belt", "suspender", "belt buckle", "waist belt", 
            "cinch belt", "sash"
        ],

        # Socks & Hosiery
        "Socks": [
            "sock", "ankle sock", "crew sock", "knee sock", "athletic sock",
            "dress sock", "compression sock", "footie", "no-show sock"
        ],
        "Hosiery": [
            "tights", "stockings", "pantyhose", "leggings", "thigh high",
            "knee high", "compression hosiery"
        ],

        # Maternity
        "Maternity": [
            "maternity", "pregnancy", "nursing", "maternal", "prenatal",
            "expecting", "maternity support", "belly band"
        ],

        # Clothing Tops (more specific)
        "Blouses": [
            "blouse", "button up", "button down", "collared shirt",
            "silk blouse", "ruffle blouse", "peasant blouse",
            "sleeveless blouse", "wrap blouse"
        ],
        "Bodysuits": [
            "bodysuit", "leotard", "one piece top", "snap bottom",
            "thong bodysuit", "long sleeve bodysuit", "tube bodysuit",
            "strapless bodysuit", "sweetheart bodysuit"
        ],
        "Tank Tops": [
            "tank top", "camisole", "sleeveless top", "spaghetti strap",
            "racerback", "muscle tank", "crop tank", "tube top", "strapless top",
            "sweetheart neck", "halter neck", "bandeau top"
        ],

        # Activewear (more specific)
        "Activewear Pants": [
            "jogger", "legging", "track pant", "sweatpant", "yoga pant",
            "athletic pant", "workout pant", "training pant"
        ],
        "Activewear Tops": [
            "sports bra", "workout top", "athletic tank", "gym shirt",
            "training top", "performance top", "crop top"
        ],
        "Activewear Jackets": [
            "track jacket", "windbreaker", "running jacket", "athletic jacket",
            "warm up jacket", "performance jacket"
        ],

        # Outerwear (more specific)
        "Vests": [
            "vest", "gilet", "sleeveless jacket", "puffer vest",
            "quilted vest", "fleece vest"
        ],
        "Rain Gear": [
            "rain coat", "rain jacket", "rain pants", "rain suit",
            "waterproof", "rainwear", "storm jacket"
        ],
        "Snow Wear": [
            "snow pants", "snow suit", "ski jacket", "snowboard pants",
            "winter gear", "insulated pants"
        ],

        # Suits & Formal Wear
        "Pant Suits": [
            "pant suit", "trouser suit", "business suit", "suit set",
            "coordinated suit", "matching suit"
        ],
        "Skirt Suits": [
            "skirt suit", "pencil skirt suit", "a-line suit",
            "business skirt set", "formal skirt suit"
        ],
        "Tuxedos": [
            "tuxedo", "dinner jacket", "formal suit", "black tie",
            "evening suit", "dress suit"
        ],

        # Underwear (more specific)
        "Boys Underwear": [
            "boys boxer", "boys brief", "boys trunk", "boys undershirt",
            "boys underpant", "boys long john"
        ],
        "Girls Underwear": [
            "girls panty", "girls brief", "girls boyshort", "girls camisole",
            "girls undershirt", "girls training bra"
        ],
        "Womens Underwear": [
            "panty", "brief", "thong", "boyshort", "hipster",
            "bikini underwear", "period underwear"
        ],

        # Add new categories for Activewear specifics
        "Activewear Pants": [
            "athletic pants", "workout pants", "training pants", "exercise pants",
            "fitness pants", "gym pants", "sport pants", "active pants"
        ],
        "Activewear Sweatshirts & Hoodies": [
            "athletic sweatshirt", "workout hoodie", "training sweatshirt",
            "gym hoodie", "sport sweatshirt", "active hoodie"
        ],
        "Activewear Tops": [
            "athletic top", "workout top", "training top", "exercise top",
            "fitness top", "gym top", "sport top", "active top"
        ],

        # Add Clothing Tops variations
        "Clothing Tops": [
            "shirt", "blouse", "top", "t-shirt", "tank top", "sweater",
            "sweatshirt", "hoodie", "cardigan", "tunic"
        ],

        # Add Loungewear specific categories
        "Loungewear": [
            "lounge", "loungewear", "lounge pants", "lounge top",
            "lounge set", "comfort wear", "house wear"
        ],
        "Loungewear Bottoms": [
            "lounge pants", "lounge shorts", "lounge leggings",
            "comfort pants", "house pants", "relaxing pants"
        ],
        "Loungewear Tops": [
            "lounge shirt", "lounge top", "comfort top",
            "house shirt", "relaxing top", "lounge sweatshirt"
        ],

        # Add Outerwear variations
        "Outerwear Coats & Jackets": [
            "coat", "jacket", "blazer", "parka", "windbreaker",
            "bomber", "denim jacket", "leather jacket", "overcoat"
        ],
        "Rain Gear": [
            "rain coat", "rain jacket", "rainwear", "waterproof jacket",
            "storm coat", "weather proof", "rain protection"
        ],

        # Add Traditional & Ceremonial variations
        "Traditional Clothing": [
            "kimono", "sari", "lehenga", "traditional dress",
            "ceremonial wear", "cultural clothing", "ethnic wear",
            "heritage garment"
        ],
        "Kimonos": [
            "kimono", "yukata", "haori", "japanese robe",
            "traditional japanese", "kimono jacket"
        ],
        "Saris & Lehengas": [
            "sari", "saree", "lehenga", "choli", "indian dress",
            "traditional indian", "ethnic dress"
        ],

        # Add specific Uniform categories
        "Food Service Uniforms": [
            "chef coat", "server uniform", "kitchen wear",
            "restaurant uniform", "cafeteria uniform"
        ],
        "Military Uniforms": [
            "military wear", "army uniform", "navy uniform",
            "air force uniform", "service uniform", "combat uniform"
        ],
        "School Uniforms": [
            "school wear", "student uniform", "academy uniform",
            "educational uniform", "school dress code"
        ],
        "Scrubs": [
            "medical scrubs", "hospital uniform", "healthcare uniform",
            "dental scrubs", "veterinary scrubs", "surgical scrubs"
        ],
        "Security Uniforms": [
            "security wear", "guard uniform", "protection uniform",
            "patrol uniform", "security officer wear"
        ],

        # Add specific Wedding categories
        "Wedding Dresses": [
            "bridal gown", "wedding gown", "bride dress",
            "marriage dress", "wedding dress", "bridal dress"
        ],
        "Bridal Party Dresses": [
            "bridesmaid dress", "maid of honor dress",
            "flower girl dress", "wedding party dress"
        ],

        # Add specific Activewear categories
        "Sports Bras": [
            "sports bra", "athletic bra", "workout bra", "training bra",
            "fitness bra", "gym bra", "high impact bra", "low impact bra"
        ],
        "Leotards & Unitards": [
            "leotard", "unitard", "dance wear", "gymnastics wear",
            "ballet leotard", "performance wear", "dance costume"
        ],
        "Boxing Shorts": [
            "boxing shorts", "fight shorts", "sparring shorts",
            "combat shorts", "ring wear", "boxing trunks"
        ],

        # Add specific Baby & Toddler categories
        "Baby & Toddler Swimwear": [
            "baby swimsuit", "toddler swimwear", "infant swim",
            "baby swim diaper", "baby rash guard", "toddler bathing suit"
        ],
        "Baby & Toddler Diaper Covers": [
            "diaper cover", "nappy cover", "diaper pants",
            "cloth diaper cover", "waterproof cover", "diaper wrap"
        ],
        "Baby & Toddler Socks & Tights": [
            "baby socks", "toddler tights", "infant socks",
            "baby stockings", "toddler leg wear", "baby booties"
        ],

        # Add Clothing Accessories categories
        "Hair Accessories": [
            "hair band", "hair clip", "hair pin", "scrunchie",
            "hair tie", "barrette", "hair bow", "headband"
        ],
        "Fashion Face Masks": [
            "face mask", "fashion mask", "decorative mask",
            "cloth mask", "reusable mask", "designer mask"
        ],
        "Arm Warmers & Sleeves": [
            "arm warmer", "sleeve cover", "arm sleeve",
            "compression sleeve", "sun sleeve", "athletic sleeve"
        ],
        "Balaclavas": [
            "balaclava", "ski mask", "face covering",
            "winter mask", "neck warmer", "full face mask"
        ],

        # Add Hat variations
        "Baseball Caps": [
            "baseball cap", "sports cap", "fitted cap",
            "adjustable cap", "structured cap", "ball cap"
        ],
        "Bucket Hats": [
            "bucket hat", "fishing hat", "sun bucket",
            "reversible bucket", "wide brim bucket", "cotton bucket hat"
        ],
        "Berets": [
            "beret", "french beret", "wool beret",
            "military beret", "artist beret", "fashion beret"
        ],
        "Fedoras": [
            "fedora", "trilby", "felt hat",
            "dress hat", "formal hat", "vintage fedora"
        ],

        # Add Shoe categories
        "Athletic Shoes": [
            "running shoe", "training shoe", "gym shoe",
            "workout shoe", "sports shoe", "fitness shoe"
        ],
        "Baby & Toddler Shoes": [
            "baby shoe", "toddler shoe", "infant footwear",
            "first walker", "crib shoe", "baby bootie"
        ],
        "Boots": [
            "boot", "ankle boot", "knee high boot",
            "winter boot", "rain boot", "hiking boot"
        ],
        "Sandals": [
            "sandal", "flip flop", "slide sandal",
            "sport sandal", "dress sandal", "beach sandal"
        ],

        # Add Shoe Accessories
        "Shoe Inserts": [
            "insole", "arch support", "heel cushion",
            "shoe pad", "orthotic insert", "comfort insert"
        ],
        "Shoelaces": [
            "laces", "shoe string", "boot lace",
            "athletic lace", "replacement lace", "decorative lace"
        ],
        "Boot Liners": [
            "boot liner", "sock liner", "boot sock",
            "winter liner", "thermal liner", "moisture wicking liner"
        ],

        # Add Handbag variations
        "Clutch Bags": [
            "clutch", "evening bag", "wristlet",
            "envelope clutch", "party clutch", "formal bag"
        ],
        "Shoulder Bags": [
            "shoulder bag", "hobo bag", "messenger bag",
            "crossbody bag", "satchel", "tote bag"
        ],
        "Mini Bags": [
            "mini bag", "small purse", "micro bag",
            "tiny bag", "coin purse", "mini crossbody"
        ],

        # Add Wallet variations
        "Card Cases": [
            "card holder", "card wallet", "business card case",
            "slim wallet", "credit card holder", "card sleeve"
        ],
        "Travel Wallets": [
            "passport wallet", "travel organizer", "document holder",
            "currency wallet", "travel pouch", "boarding pass holder"
        ],
        "Coin Purses": [
            "coin holder", "change purse", "small pouch",
            "zip coin purse", "money holder", "mini wallet"
        ],

        # Add Lingerie & Underwear categories
        "Bra Accessories": [
            "bra strap", "bra extender", "bra pad", "bra insert",
            "breast enhancer", "nipple cover", "bra converter"
        ],
        "Shapewear": [
            "body shaper", "waist cincher", "slimming garment",
            "control top", "compression wear", "body suit", "girdle"
        ],
        "Petticoats & Pettipants": [
            "petticoat", "crinoline", "underskirt", "pettipant",
            "slip shorts", "bloomers", "dance pettiskirt"
        ],
        "Men's Underwear": [
            "boxer brief", "trunk", "boxer short", "brief",
            "jockstrap", "thong", "g-string", "undershort"
        ],

        # Add specific Swimwear categories
        "Burkinis": [
            "burkini", "modest swimwear", "full coverage swimsuit",
            "islamic swimwear", "muslim swimwear", "hijab swimsuit"
        ],
        "Classic Bikinis": [
            "bikini set", "two piece swimsuit", "triangle bikini",
            "halter bikini", "bandeau bikini", "string bikini"
        ],
        "Swim Dresses": [
            "swim dress", "swimming dress", "beach dress",
            "skirted swimsuit", "swim skirt", "tankini dress"
        ],
        "Surf Tops": [
            "surf shirt", "swim shirt", "beach top",
            "water shirt", "sun protection top", "uv protection shirt"
        ],

        # Add Pants variations
        "Cargo Pants": [
            "cargo", "utility pants", "military style pants",
            "pocket pants", "tactical pants", "combat pants"
        ],
        "Chinos": [
            "chino pants", "khakis", "casual pants",
            "cotton twill pants", "flat front pants", "dress casual pants"
        ],
        "Jeggings": [
            "jean legging", "stretch jean", "denim legging",
            "pull-on jean", "elastic waist jean", "skinny jean"
        ],
        "Joggers": [
            "jogger pant", "sweat pant", "track pant",
            "athletic pant", "cuffed pant", "drawstring pant"
        ],

        # Add Shorts variations
        "Bermudas": [
            "bermuda short", "walking short", "knee length short",
            "dress short", "tailored short", "city short"
        ],
        "Cargo Shorts": [
            "cargo short", "utility short", "pocket short",
            "military style short", "tactical short", "combat short"
        ],
        "Denim Shorts": [
            "jean short", "cutoff short", "denim cutoff",
            "jean cutoff", "distressed short", "frayed short"
        ],
        "Legging Shorts": [
            "bike short", "cycling short", "compression short",
            "athletic short", "yoga short", "spandex short"
        ],

        # Add Sock variations
        "Ankle Socks": [
            "low cut sock", "no show sock", "trainer sock",
            "invisible sock", "liner sock", "peds"
        ],
        "Athletic Socks": [
            "sport sock", "performance sock", "gym sock",
            "training sock", "moisture wicking sock", "cushioned sock"
        ],
        "Crew Socks": [
            "mid calf sock", "regular sock", "classic sock",
            "business sock", "casual sock", "everyday sock"
        ],
        "Dance Socks": [
            "ballet sock", "dance footie", "performance sock",
            "grip sock", "studio sock", "dance pad"
        ],

        # Add Costume categories
        "Costume Sets": [
            "complete costume", "character outfit", "costume bundle",
            "dress up set", "themed costume", "holiday costume"
        ],
        "Costume Accessories": [
            "costume prop", "character accessory", "costume jewelry",
            "costume makeup", "costume wig", "costume mask"
        ],
        "Costume Shoes": [
            "character shoes", "costume boots", "theatrical footwear",
            "dress up shoes", "performance shoes", "cosplay shoes"
        ],

        # Add more specific cardigan variations
        "Long Cardigans": [
            "longline cardigan", "long cardigan", "maxi cardigan", 
            "duster cardigan", "full length cardigan", "open front long cardigan"
        ],
        "Button Up Cardigans": [
            "button up cardigan", "button down cardigan", "button front cardigan",
            "buttoned cardigan", "snap front cardigan", "closure cardigan"
        ],

        # Add more specific crop top variations
        "Crop Tops": [
            "crop top", "cropped top", "short top", "midriff top",
            "belly top", "abbreviated top", "crop shirt"
        ],
        "Long Sleeve Crop Tops": [
            "long sleeve crop", "cropped long sleeve", "long sleeve short top",
            "crop sweater top", "cropped sleeve top"
        ],

        # Add more specific overall variations
        "Wide Leg Overalls": [
            "wide leg overall", "wide overalls", "loose fit overall",
            "baggy overall", "palazzo overall", "flare overall"
        ],
        "Textured Overalls": [
            "textured overall", "ribbed overall", "knit overall",
            "woven overall", "patterned overall"
        ],

        # Add more specific pant variations
        "Wide Leg Pants": [
            "wide leg", "palazzo pant", "wide trouser", "flare leg",
            "loose fit pant", "wide cut pant"
        ],
        "Cargo Wide Leg Pants": [
            "cargo wide leg", "wide cargo pant", "loose cargo",
            "utility wide leg", "baggy cargo"
        ],

        # Add more specific top variations
        "Bubble Hem Tops": [
            "bubble hem", "puff hem top", "gathered hem",
            "balloon hem", "elastic hem top"
        ],
        "Eyelet Tops": [
            "eyelet top", "eyelet lace", "broderie anglaise",
            "perforated top", "cutout embroidery"
        ],
        "Frill Tops": [
            "frill top", "ruffle top", "frilled shirt",
            "ruffle detail", "frill trim", "ruffle trim"
        ],

        # Add more specific dress variations
        "Babydoll Dresses": [
            "babydoll dress", "baby doll", "empire waist dress",
            "smock dress", "swing dress", "trapeze dress"
        ],
        "Cami Dresses": [
            "cami dress", "spaghetti strap dress", "slip dress",
            "sleeveless dress", "strap dress", "thin strap dress"
        ],
        "Eyelet Dresses": [
            "eyelet dress", "lace dress", "broderie dress",
            "perforated dress", "cutout embroidery dress"
        ],

        # Add more specific set variations
        "Two Piece Sets": [
            "two piece set", "matching set", "coord set",
            "top and bottom set", "two piece outfit", "set combo"
        ],
        "Crop Top Sets": [
            "crop top set", "cropped set", "crop and shorts",
            "crop and skirt", "crop and pants", "cropped combo"
        ]
    }

    # Gender-specific clothing types
    FEMININE_CLOTHING = [
        'dress', 'skirt', 'blouse', 'cami', 'bra', 'lingerie', 
        'leggings', 'womens', 'women', 'feminine', 'girl', 'girls'
    ]
    
    MASCULINE_CLOTHING = {
        'suit', 'tuxedo', 'blazer', 'necktie', 'bow tie',
        'cargo pants', 'board shorts', 'muscle tank'
    }

    # Add common value variations
    VALUE_VARIATIONS = {
        'Stretchable': ['stretch', 'stretchy', 'elastic', 'flexible'],
        'Long': ['full length', 'maxi', 'longline', 'floor length'],
        'Short': ['cropped', 'crop', 'mini'],
        'Medium': ['mid length', 'midi', 'knee length'],
    }

    # Define base categories as a class constant
    BASE_CATEGORIES = {
        'Cardigans': {
            'patterns': [
                (r'\bcardigan\b', 2.5),
                (r'open[\s-]front', 2.5),
                (r'button[\s-](?:up|down)[\s-](?:cardigan|sweater)', 2.8),
                (r'long[\s-]sleeve[\s-](?:cardigan|sweater)', 2.8),
                (r'longline[\s-]cardigan', 2.8),
                (r'cropped[\s-]cardigan', 2.8),
                (r'hooded[\s-]cardigan', 2.8),
                (r'duster[\s-]cardigan', 2.8),
                (r'(?:chunky|cable[\s-]knit)[\s-]cardigan', 2.8)
            ],
            'path': 'Apparel & Accessories > Clothing > Clothing Tops > Cardigans'
        },
        'Dresses': {
            'patterns': [
                (r'\bdress\b', 2.5),
                (r'(?:mini|midi|maxi)[\s-](?:dress|length)', 2.8),
                (r'(?:tiered|layered|ruffled|smocked)[\s-]dress', 2.8),
                (r'(?:halter|v[\s-]neck|off[\s-]shoulder).*dress', 2.8),
                (r'(?:button[\s-](?:up|down)|shirt)[\s-]dress', 2.8),
                (r'(?:babydoll|cami|a-line)[\s-]dress', 2.8),
                (r'high[\s-]low.*dress', 2.8),
                (r'(?:puff|flutter)[\s-]sleeve.*dress', 2.8),
                (r'gown', 2.5),
                (r'frock', 2.5)
            ],
            'path': 'Apparel & Accessories > Clothing > Dresses'
        },
        'Hoodies': {
            'patterns': [
                (r'\bhoodie\b', 2.5),
                (r'hooded[\s-](?:sweatshirt|top)', 2.8),
                (r'drawstring[\s-]hood', 2.8),
                (r'kangaroo[\s-]pocket', 2.5),
                (r'zip[\s-]up[\s-]hood', 2.8),
                (r'pullover[\s-]hood', 2.8)
            ],
            'path': 'Apparel & Accessories > Clothing > Clothing Tops > Hoodies'
        },
        'Sweatshirts': {
            'patterns': [
                (r'\bsweatshirt\b', 2.5),
                (r'pullover(?![\s-]hood)', 2.5),  # Exclude hooded pullovers
                (r'(?:half|quarter)[\s-]zip', 2.8),
                (r'raglan[\s-]sleeve', 2.5),
                (r'crew[\s-]neck[\s-]sweat', 2.8),
                (r'fleece[\s-]top', 2.5)
            ],
            'path': 'Apparel & Accessories > Clothing > Clothing Tops > Sweatshirts'
        },
        'Windbreakers': {
            'terms': ['windbreaker', 'wind breaker', 'wind jacket'],
            'excludes': ['dress', 'set'],
            'weight': 20.0,
            'path': 'Apparel & Accessories > Clothing > Outerwear > Coats & Jackets > Windbreakers'
        },
        'Coats & Jackets': {
            'terms': ['jacket', 'coat', 'blazer', 'rider jacket', 'worker jacket', 'corduroy jacket'],
            'excludes': ['dress', 'set', 'wind'],
            'weight': 20.0,
            'path': 'Apparel & Accessories > Clothing > Outerwear > Coats & Jackets'
        },
        # ... other existing categories ...
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
        for attr, values in ATTRIBUTE_PATTERNS.items():
            attr_patterns = {}
            for value, pattern in values.items():
                attr_patterns[value] = re.compile(pattern, re.IGNORECASE)
            self.attribute_patterns[attr] = attr_patterns

    def get_category_info(self, title: str, description: str = "") -> Dict:
        """Get category info for a product based on title and description"""
        # Normalize text for matching
        text = f"{title} {description}".lower()
        
        # Check for outfit sets first - before any other matching
        set_pattern = r'\b(?:two[\s-]piece\s+)?set\b(?:\s+(?:of|with|and)\b)?'
        set_match = re.search(set_pattern, text.lower())
        
        # Skip if it's part of other words
        skip_terms = ['setting', 'mindset', 'sunset', 'preset', 'settee']
        is_valid_set = set_match and not any(skip in text.lower() for skip in skip_terms)
        
        # Check for clothing terms that suggest it's an outfit set
        clothing_terms = [
            'top', 'bottom', 'piece', 'shirt', 'pant', 'short', 'skirt',
            'dress', 'crop', 'tank', 'bra', 'jacket', 'cardigan'
        ]
        
        # Also avoid matching explicit suit terms
        suit_terms = ['pant suit', 'skirt suit', 'tuxedo', 'suit jacket', 'blazer']
        is_not_suit = not any(term in text.lower() for term in suit_terms)
        
        if is_valid_set and is_not_suit and any(term in text.lower() for term in clothing_terms):
            logger.debug(f"Found outfit set match in: '{text}'")
            # Return Outfit Sets info with correct GID
            outfit_set = {
                'category': 'Outfit Sets',
                'path': 'Apparel & Accessories > Clothing > Outfit Sets',
                'gid': 'gid://shopify/TaxonomyCategory/aa-1-11',  # Updated to correct GID
                'keyword': 'set',
                'exact_match': True,
                'score': 2.0  # High confidence for explicit set matches
            }
            logger.debug(f"Matched 'set' to Outfit Sets (confidence: 2.0)")
            return outfit_set
        
        matches = []
        # Try exact category matches first
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if re.search(rf"\b{keyword}\b", text):
                    logger.debug(f"Found keyword match: {keyword} for category {category}")
                    
                    # Find matching path info from CATEGORY_PATHS
                    for path, path_info in CATEGORY_PATHS.items():
                        if path.split(' > ')[-1] == category:
                            matches.append({
                                'category': category,
                                'path': path_info['path'],
                                'gid': path_info['gid'],
                                'keyword': keyword,
                                'exact_match': True
                            })
                            break

        # If no exact matches, try fallback categories
        if not matches:
            for path, path_info in CATEGORY_PATHS.items():
                # Skip any paths with "Baby & Toddler"
                if "Baby & Toddler" in path_info['path']:
                    continue
                    
                category = path.split(' > ')[-1]
                # Try matching category name as keyword
                if re.search(rf"\b{category.lower()}\b", text):
                    logger.debug(f"Found fallback match: {category} from path {path}")
                    matches.append({
                        'category': category,
                        'path': path_info['path'],
                        'gid': path_info['gid'],
                        'keyword': category,
                        'exact_match': False
                    })

        if not matches:
            logger.debug(f"No category matches found for: {title}")
            return {}

        # Score matches and select best one
        def score_category(match: Dict) -> float:
            score = 0.0
            
            # Base score based on match type
            if match.get('exact_match'):
                score += 0.5  # Higher base score for exact category matches
            else:
                score -= 0.2  # Penalty for fallback matches
            
            # Keyword quality scoring
            keyword = match['keyword'].lower()
            title_lower = title.lower()
            
            # Bonus for keyword position (earlier is better)
            position = title_lower.find(keyword)
            if position != -1:
                position_score = 1.0 - (position / len(title_lower))  # 1.0 to 0.0 based on position
                score += position_score * 0.3
            
            # Bonus for keyword length (longer matches are more confident)
            word_count = len(keyword.split())
            score += word_count * 0.15
            
            # Count multiple occurrences
            occurrences = len(re.findall(rf"\b{re.escape(keyword)}\b", text))
            score += min(occurrences - 1, 2) * 0.2  # Cap bonus at 2 extra occurrences
            
            # Word overlap scoring
            title_words = set(title_lower.split())
            keyword_words = set(keyword.split())
            overlap = len(keyword_words & title_words)
            overlap_ratio = overlap / len(keyword_words)
            score += overlap_ratio * 0.4
            
            # Extra confidence for exact phrase matches
            if keyword in title_lower:
                score += 0.3
            
            # Penalize generic single-word fallback matches
            if not match.get('exact_match') and word_count == 1:
                score -= 0.3
                
            # Normalize score to reasonable range
            return max(min(score, 2.0), 0.1)  # Cap between 0.1 and 2.0

        # Get best match and attach score
        best_match = max(matches, key=score_category)
        best_match['score'] = score_category(best_match)
        
        logger.debug(f"Selected category: {best_match['category']} (path: {best_match['path']}, score: {best_match['score']})")
        return best_match

    def _get_category_matches(self, title: str, description: str) -> List[Tuple[str, float]]:
        """Get all matching categories with confidence scores"""
        title = title.lower()
        description = description.lower()
        matches = []

        # Super clear indicators with massive weights
        clear_indicators = {
            # Add Leggings before other pants categories
            'Leggings': {
                'terms': ['legging', 'leggings', 'yoga pants', 'workout pants', 'athletic pants'],
                'excludes': ['dress', 'set', 'top'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Activewear > Activewear Pants > Leggings'
            },
            # Add Windbreakers before Coats & Jackets
            'Windbreakers': {
                'terms': ['windbreaker', 'wind breaker', 'wind jacket'],
                'excludes': ['dress', 'set'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Outerwear > Coats & Jackets > Windbreakers'
            },
            'Coats & Jackets': {
                'terms': ['jacket', 'coat', 'blazer', 'rider jacket', 'worker jacket', 'corduroy jacket'],
                'excludes': ['dress', 'set', 'wind'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Outerwear > Coats & Jackets'
            },
            'One-Pieces': {
                'terms': ['jumpsuit', 'romper', 'overalls', 'playsuit'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > One-Pieces'
            },
            'Outfit Sets': {
                'terms': [' and ', ' set'],
                'requires': ['top', 'cami', 'blouse', 'shorts', 'pants', 'skirt'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Outfit Sets'
            },
            'Pants': {
                'terms': ['pants', 'jeans', 'wide leg pants', 'cargo pants', 'yoga pants', 'ankle jeans'],
                'excludes': ['set', 'jumpsuit', 'overall'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Pants'
            },
            'Blouses': {
                'terms': ['blouse', 'button down blouse', 'silk blouse', 'flounce sleeve', 'bubble sleeve'],
                'excludes': ['dress', 'set'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Clothing Tops > Blouses'
            },
            'Shirts': {
                'terms': ['button down shirt', 'button up shirt', 'long sleeve shirt', 'button down'],
                'excludes': ['dress', 'set'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Clothing Tops > Shirts'
            },
            'Basic Tops': {
                'terms': ['sleeveless top', 'tube top', 'tank top', 'frill top', 'crop top', 'cami', 'knit top', 'ruffle sleeve top', 'color block top'],
                'excludes': ['dress', 'set', 'cardigan', 'jumpsuit'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Clothing Tops'
            },
            'T-Shirts': {
                'terms': ['t-shirt', 't shirt', 'tee'],
                'excludes': ['dress', 'set'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Clothing Tops > T-Shirts'
            },
            'Dresses': {
                'terms': ['dress', 'midi dress', 'mini dress', 'maxi dress'],
                'excludes': ['shirt', 'top'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Dresses'
            },
            'Skirts': {
                'terms': ['skirt', 'midi skirt', 'mini skirt', 'maxi skirt'],
                'excludes': ['set', 'dress'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Skirts'
            },
            'Shorts': {
                'terms': ['shorts', 'bermuda shorts', 'cargo shorts'],
                'excludes': ['set', 'overall'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Shorts'
            },
            'Cardigans': {
                'terms': ['cardigan'],
                'excludes': ['dress', 'set'],
                'weight': 15.0,
                'path': 'Apparel & Accessories > Clothing > Clothing Tops > Cardigans'
            },
            'Flannel Shirts': {
                'terms': ['flannel shirt', 'plaid shirt', 'button up flannel', 'button down flannel'],
                'excludes': ['dress', 'set'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Clothing Tops > Shirts'
            },
            'Sweaters': {
                'terms': ['sweater', 'pullover', 'cardigan', 'cover up', 'knit cover'],
                'excludes': ['dress', 'set', 'swimsuit', 'tank', 'cami', 'shorts', 'pants', 'skirt', 't-shirt', 'swim cover'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Clothing Tops > Sweaters'
            },
            'Tank Tops': {
                'terms': ['tank', 'cami', 'sleeveless'],
                'excludes': ['dress', 'set', 'swimsuit', 'cover up', 'shorts', 'pants', 'skirt', 'sleeve'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Clothing Tops > Tank Tops'
            },
            'Tank Dresses': {
                'terms': ['tank', 'dress'],
                'excludes': ['top', 'shirt', 'blouse', 'sweater', 'jacket'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Dresses > Tank Dresses'
            },
            'Tank Sets': {
                'terms': ['tank', 'set'],
                'excludes': ['dress', 'sweater', 'jacket', 'coat'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Outfit Sets > Tank Sets'
            },
            'Swim Cover Ups': {
                'terms': ['swim cover', 'beach cover', 'swimsuit cover'],
                'excludes': ['sweater', 'jacket'],
                'weight': 20.0,
                'path': 'Apparel & Accessories > Clothing > Swimwear > Cover Ups'
            }
        }

        # Check super clear indicators first
        for category, info in clear_indicators.items():
            if any(term in title for term in info['terms']):
                if 'requires' in info:
                    if any(req in title for req in info['requires']):
                        return [(info['path'], info['weight'])]
                elif 'excludes' in info:
                    if not any(excl in title for excl in info['excludes']):
                        return [(info['path'], info['weight'])]
                else:
                    return [(info['path'], info['weight'])]

        # Regular pattern matching with strong category boosts
        for category, info in self.BASE_CATEGORIES.items():
            score = 0
            title_match = False
            desc_match = False

            # Pattern matching
            for pattern, weight in info['patterns']:
                if re.search(pattern, title):
                    score += weight * 1.5
                    title_match = True
                elif re.search(pattern, description):
                    score += weight
                    desc_match = True

            # Category-specific massive boosts
            if category == 'Tops':
                if any(x in title for x in ['top', 'sleeveless', 'tube', 'tank', 'frill', 'crop', 'cami', 'knit']):
                    score *= 5.0  # Huge boost for tops
                if any(x in title for x in ['neck', 'sweetheart', 'round', 'grecian']):
                    score *= 2.0  # Additional boost for neckline mentions
            elif category == 'Pants':
                if any(x in title for x in ['pants', 'jeans', 'wide leg', 'cargo', 'yoga', 'ankle']):
                    score *= 5.0  # Huge boost for pants

            # Competing category reductions
            if any(x in title for x in ['dress', 'jumpsuit', 'cardigan', 'overall']) and category == 'Tops':
                score *= 0.2  # Strong reduction for competing categories

            if score > 0:
                matches.append((info['path'], score))

        # If no matches found but contains 'top', default to Tops
        if not matches and ('top' in title or 'cami' in title or 'sleeve' in title):
            return [('Apparel & Accessories > Clothing > Clothing Tops', 8.0)]

        return matches

    def categorize(self, title: str, description: str) -> Tuple[Optional[str], float]:
        """Get best matching category"""
        try:
            matches = self._get_category_matches(title, description)
            
            if not matches:
                logger.warning(f"No category matches found for product: {title}")
                return None, 0.0
            
            # Get best match
            best_path, confidence = matches[0]
            logger.debug(f"Selected best category: {best_path} (confidence: {confidence})")
            
            # Get category ID from path
            category_id = self.mapper.get_category_id_from_path(best_path)
            if not category_id:
                logger.warning(f"No category ID found for path: {best_path}")
                return None, 0.0
            
            return category_id, confidence
            
        except Exception as e:
            logger.error(f"Error categorizing product '{title}': {str(e)}")
            return None, 0.0

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

    def _extract_size_from_variants(self, product: Dict) -> Optional[str]:
        """Extract size value from product variants"""
        # First check options for size
        for option in product.get('options', []):
            if option.get('name') == 'Size':
                # Get first size value
                size_values = option.get('values', [])
                if size_values:
                    return size_values[0]
                
        # Then check variant selected options
        for variant in product.get('variants', []):
            for option in variant.get('selected_options', []):
                if option.get('name') == 'Size':
                    return option.get('value')
                    
        return None

    def _extract_fabric_values(self, text: str) -> List[str]:
        """Extract fabric values from text, including percentages"""
        fabrics = []
        
        # Look for fabric percentages
        fabric_percent_pattern = r'(\d+)%\s*([\w-]+)'
        matches = re.findall(fabric_percent_pattern, text.lower())
        for percentage, fabric in matches:
            fabric = fabric.strip()
            # Check if this fabric has a matching pattern
            for fabric_name, pattern in ATTRIBUTE_PATTERNS['fabric'].items():
                if re.search(pattern, fabric):
                    fabrics.append(fabric_name)
                    break
        
        # Also check for fabric mentions without percentages
        for fabric_name, pattern in ATTRIBUTE_PATTERNS['fabric'].items():
            if re.search(pattern, text.lower()):
                if fabric_name not in fabrics:
                    fabrics.append(fabric_name)
        
        return fabrics

    def get_suggested_attributes(self, title: str, description: str, product: Dict = None) -> Dict:
        """Get suggested attributes for a product"""
        # Add debug logging
        logger.debug(f"Getting suggested attributes for title: {title}")
        
        # Get category first
        category_id, confidence = self.categorize(title, description)
        if not category_id:
            logger.warning("No category found")
            return {}
        
        # Get category path
        category_path = self.mapper.get_path_from_category_id(category_id)
        
        # Get allowed attributes for category
        allowed_attrs = self.mapper.get_allowed_attribute_ids(category_id)
        logger.debug(f"Allowed attributes: {allowed_attrs}")
        
        # Build attributes dict
        attributes = {
            'category': {
                'gid': category_id,
                'path': category_path,
                'confidence': confidence
            }
        }
        
        # Add attribute values
        for attr_id in allowed_attrs:
            value = self._get_attribute_value(title, description, attr_id, product)
            if value:
                attributes[attr_id] = value
                logger.debug(f"Added attribute {attr_id}: {value}")
        
        logger.debug(f"Final attributes: {attributes}")
        return attributes

    def _get_attribute_value(self, title: str, description: str, attr_id: str, product: Dict = None) -> Optional[List[str]]:
        """Get value(s) for a specific attribute"""
        text = f"{title} {description}".lower()
        
        # Get attribute handle
        attr_handle = self.mapper.get_handle_from_attribute_id(attr_id)
        if not attr_handle:
            logger.debug(f"No handle found for attribute {attr_id}")
            return None

        logger.debug(f"Processing attribute {attr_handle} ({attr_id})")
        
        # Handle one-piece style
        if attr_handle == "one-piece-style":
            style_patterns = {
                'overall': r'\boverall(?:s)?\b|\boverall[\s-]dress\b',
                'jumpsuit': r'\bjumpsuit\b|\bjump[\s-]suit\b',
                'playsuit': r'\bplaysuit\b|\bplay[\s-]suit\b',
                'romper': r'\bromper\b',
                'dungaree': r'\bdungaree(?:s)?\b',
                'coverall': r'\bcoverall(?:s)?\b',
                'boiler-suit': r'\bboiler[\s-]suit\b',
                'catsuit': r'\bcatsuit\b',
                'unitard': r'\bunitard\b',
                'leotard': r'\bleotard\b',
                'salopette': r'\bsalopette\b',
                'bodysuit': r'\bbodysuit\b|body[\s-]suit',
                'other': r'one[\s-]piece|full[\s-]body'
            }
            
            # Check title first with higher priority
            title_text = text.split(description)[0] if description in text else text
            for style, pattern in style_patterns.items():
                if re.search(pattern, title_text):
                    value_id = self.mapper.get_value_id_by_name(attr_id, style)
                    if value_id:
                        logger.debug(f"Found one-piece style in title: {style} -> {value_id}")
                        return [value_id]
            
            # Then check full text
            for style, pattern in style_patterns.items():
                if re.search(pattern, text):
                    value_id = self.mapper.get_value_id_by_name(attr_id, style)
                    if value_id:
                        logger.debug(f"Found one-piece style: {style} -> {value_id}")
                        return [value_id]
            return None

        # Handle size - collect all matching sizes
        if attr_handle == "size" and product:
            sizes = []
            # Map variant sizes to short handles
            size_mappings = {
                'small': 's',
                'small (s)': 's',
                'small-s': 's',
                's': 's',
                'medium': 'm',
                'medium (m)': 'm', 
                'medium-m': 'm',
                'm': 'm',
                'large': 'l',
                'large (l)': 'l',
                'large-l': 'l',
                'l': 'l',
                'extra small': 'xs',
                'xs': 'xs',
                'extra large': 'xl',
                'xl': 'xl',
                '2xl': '2xl',
                'xxl': '2xl',
                '3xl': '3xl',
                'xxxl': '3xl',
                '4xl': '4xl',
                '5xl': '5xl'
            }
            
            # Check variants for sizes
            for variant in product.get('variants', []):
                for option in variant.get('selected_options', []):
                    if option.get('name') == 'Size':
                        size_value = option.get('value', '').lower()
                        # Map to short handle
                        short_handle = size_mappings.get(size_value)
                        if short_handle:
                            logger.debug(f"Mapping size {size_value} to {short_handle}")
                            value_id = self.mapper.get_value_id_by_name(attr_id, short_handle)
                            if value_id and value_id not in sizes:
                                sizes.append(value_id)
                                logger.debug(f"Found size from variant: {short_handle} -> {value_id}")
            
            return sizes if sizes else None

        # Handle fabric - collect all fabrics
        if attr_handle == "fabric":
            fabrics = []
            fabric_patterns = {
                'rayon': r'\brayon\b',
                'polyester': r'\bpolyester\b',
                'cotton': r'\bcotton\b',
                'linen': r'\blinen\b|\blinen[\s-]blend\b',
                'silk': r'\bsilk\b',
                'nylon': r'\bnylon\b',
                'spandex': r'\bspandex\b'
            }
            
            # Look for percentages
            matches = re.findall(r'(\d+)%\s*([\w-]+(?:\s+blend)?)', text)
            for percentage, fabric in matches:
                fabric = fabric.strip()
                for fabric_name, pattern in fabric_patterns.items():
                    if re.search(pattern, fabric):
                        value_id = self.mapper.get_value_id_by_name(attr_id, fabric_name)
                        if value_id and value_id not in fabrics:
                            fabrics.append(value_id)
                            logger.debug(f"Found fabric from percentage: {fabric_name} -> {value_id}")
            
            # Also check for fabric mentions without percentages
            for fabric_name, pattern in fabric_patterns.items():
                if re.search(pattern, text):
                    value_id = self.mapper.get_value_id_by_name(attr_id, fabric_name)
                    if value_id and value_id not in fabrics:
                        fabrics.append(value_id)
                        logger.debug(f"Found fabric from text: {fabric_name} -> {value_id}")
            
            return fabrics if fabrics else None

        # Handle target gender
        if attr_handle == "target-gender":
            if any(word in text for word in self.FEMININE_CLOTHING):
                return [self.mapper.get_value_id_by_name(attr_id, "female")]
            return None
        
        # Handle skirt/dress length
        if attr_handle == "skirt-dress-length-type":
            length_patterns = {
                'mini': r'\bmini\b',
                'midi': r'\bmidi\b',
                'maxi': r'\bmaxi\b',
                'knee length': r'knee[\s-]length'
            }
            
            for length, pattern in length_patterns.items():
                if re.search(pattern, text):
                    value_id = self.mapper.get_value_id_by_name(attr_id, length)
                    if value_id:
                        logger.debug(f"Found length: {length} -> {value_id}")
                        return [value_id]
            return None
        
        # Handle waist rise
        if attr_handle == "waist-rise":
            rise_patterns = {
                'high': r'high[\s-]rise|high[\s-]waist',
                'mid': r'mid[\s-]rise|mid[\s-]waist',
                'low': r'low[\s-]rise|low[\s-]waist'
            }
            
            for rise, pattern in rise_patterns.items():
                if re.search(pattern, text):
                    value_id = self.mapper.get_value_id_by_name(attr_id, rise)
                    if value_id:
                        logger.debug(f"Found rise: {rise} -> {value_id}")
                        return [value_id]
            return None
        
        # Handle sleeve length
        if attr_handle == "sleeve-length-type":
            sleeve_patterns = {
                'cap': r'cap\s*sleeve',
                '3-4': r'three[\s-]quarter|3/4|3-4',
                'long': r'long\s*sleeve',
                'short': r'short\s*sleeve',
                'sleeveless': r'sleeveless',
                'spaghetti-strap': r'spaghetti[\s-]strap',
                'strapless': r'strapless'
            }
            
            for length, pattern in sleeve_patterns.items():
                if re.search(pattern, text):
                    value_id = self.mapper.get_value_id_by_name(attr_id, length)
                    if value_id:
                        logger.debug(f"Found sleeve length: {length} -> {value_id}")
                        return [value_id]
            return None
        
        # Handle top length
        if attr_handle == "top-length-type":
            length_patterns = {
                'crop-top': r'crop(?:ped)?[\s-](?:top|length)|crop(?:ped)?',
                'long': r'long[\s-](?:top|length)|tunic[\s-]length',
                'medium': r'medium[\s-](?:top|length)|regular[\s-]length|standard[\s-]length',
                'bodysuit': r'bodysuit|body[\s-]suit',
                'other': r'high[\s-]low|asymmetric(?:al)?'
            }
            
            for length, pattern in length_patterns.items():
                if re.search(pattern, text):
                    value_id = self.mapper.get_value_id_by_name(attr_id, length)
                    if value_id:
                        logger.debug(f"Found top length: {length} -> {value_id}")
                        return [value_id]
            return None
        
        # Handle skirt styles
        if attr_handle == "skirt-style":
            style_patterns = {
                'bracer': r'bracer|suspender[\s-]skirt',
                'circle': r'circle[\s-]skirt|full[\s-]circle|skater[\s-]skirt',
                'denim': r'denim[\s-]skirt|jean[\s-]skirt',
                'gathered': r'gather(?:ed)?|ruch(?:ed)?|shirr(?:ed)?|bubble[\s-]skirt',
                'kilt': r'kilt|pleated[\s-]wrap',
                'layered': r'layer(?:ed)?|tier(?:ed)?',
                'pencil': r'pencil[\s-]skirt|fitted[\s-]skirt',
                'pleated': r'pleat(?:ed)?|accordion[\s-]pleat',
                'plisse': r'plisse|micro[\s-]pleat',
                'prairie': r'prairie|boho[\s-]style|peasant[\s-]style',
                'sheath': r'sheath|straight[\s-]cut',
                'skirtall': r'skirtall|overall[\s-]skirt',
                'tailored': r'tailor(?:ed)?|structured',
                'tutu': r'tutu|ballet[\s-]skirt',
                'wrap': r'wrap[\s-](?:around|style)|sarong[\s-]style',
                'other': r'asymmetric|handkerchief|high[\s-]low'
            }
            
            for style, pattern in style_patterns.items():
                if re.search(pattern, text):
                    value_id = self.mapper.get_value_id_by_name(attr_id, style)
                    if value_id:
                        logger.debug(f"Found skirt style: {style} -> {value_id}")
                        return [value_id]
            return None
        
        # Handle neckline types
        if attr_handle == "neckline":
            neckline_patterns = {
                'asymmetric': r'asymmetric(?:al)?[\s-]neck|one[\s-]shoulder',
                'bardot': r'bardot|off[\s-](?:the[\s-])?shoulder',
                'boat': r'boat[\s-]neck|bateau',
                'cowl': r'cowl[\s-]neck|drape[\s-]neck',
                'crew': r'crew[\s-]neck|round[\s-]crew',
                'halter': r'halter[\s-](?:neck|top)|tie[\s-]neck',
                'hooded': r'hood(?:ed|ie)|drawstring[\s-]hood',
                'mandarin': r'mandarin[\s-]collar|band[\s-]collar|stand[\s-]collar',
                'mock': r'mock[\s-](?:neck|turtleneck)|half[\s-]turtleneck',
                'plunging': r'plunging[\s-](?:neck|neckline)|deep[\s-]v',
                'round': r'\bround[\s-]neck\b|\bscoop[\s-]neck\b',
                'split': r'split[\s-]neck|keyhole[\s-]neck',
                'square': r'square[\s-]neck',
                'sweetheart': r'sweetheart[\s-]neck|heart[\s-]shape',
                'turtle': r'turtle[\s-]neck|roll[\s-]neck',
                'v-neck': r'v[\s-]neck|v[\s-]shape',
                'wrap': r'wrap[\s-](?:neck|style|front)',
                'other': r'unique[\s-]neck|special[\s-]neck'
            }
            
            # Check title first with higher priority
            title_text = text.split(description)[0] if description in text else text
            for neckline, pattern in neckline_patterns.items():
                if re.search(pattern, title_text, re.IGNORECASE):
                    value_id = self.mapper.get_value_id_by_name(attr_id, neckline)
                    if value_id:
                        logger.debug(f"Found neckline in title: {neckline} -> {value_id}")
                        return [value_id]
            
            # Then check full text
            for neckline, pattern in neckline_patterns.items():
                if re.search(pattern, text, re.IGNORECASE):
                    value_id = self.mapper.get_value_id_by_name(attr_id, neckline)
                    if value_id:
                        logger.debug(f"Found neckline: {neckline} -> {value_id}")
                        return [value_id]
            
            # Try to infer from common phrases
            if re.search(r'collar', text, re.IGNORECASE):
                value_id = self.mapper.get_value_id_by_name(attr_id, 'mandarin')
                if value_id:
                    logger.debug(f"Inferred mandarin neckline from collar mention")
                    return [value_id]
                
            return None

        return None

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