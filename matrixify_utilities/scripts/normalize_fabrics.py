import re
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class FabricNormalizer:
    def __init__(self):
        # Standard fabric mappings with regex patterns and Shopify taxonomy IDs
        self.fabric_mappings = {
            r'(?i)\bacrylic\b': ('Acrylic', 'gid://shopify/TaxonomyValue/16980'),
            r'(?i)\bangora\b': ('Angora', 'gid://shopify/TaxonomyValue/603'),
            r'(?i)\bbamboo\b': ('Bamboo', 'gid://shopify/TaxonomyValue/16981'),
            r'(?i)\bcanvas\b': ('Canvas', 'gid://shopify/TaxonomyValue/16982'),
            r'(?i)\bcashmere\b': ('Cashmere', 'gid://shopify/TaxonomyValue/66'),
            r'(?i)\bcorduroy\b': ('Corduroy', 'gid://shopify/TaxonomyValue/606'),
            r'(?i)\bcork\b': ('Cork', 'gid://shopify/TaxonomyValue/16983'),
            r'(?i)\bcotton\b': ('Cotton', 'gid://shopify/TaxonomyValue/16984'),
            r'(?i)\bdenim\b': ('Denim', 'gid://shopify/TaxonomyValue/54'),
            r'(?i)\bfaux[\s-]?fur\b': ('Faux fur', 'gid://shopify/TaxonomyValue/594'),
            r'(?i)\bfaux[\s-]?leather\b': ('Faux leather', 'gid://shopify/TaxonomyValue/16985'),
            r'(?i)\bfelt\b': ('Felt', 'gid://shopify/TaxonomyValue/16986'),
            r'(?i)\bflannel\b': ('Flannel', 'gid://shopify/TaxonomyValue/556'),
            r'(?i)\bfleece\b': ('Fleece', 'gid://shopify/TaxonomyValue/555'),
            r'(?i)\bfur\b': ('Fur', 'gid://shopify/TaxonomyValue/63'),
            r'(?i)\bhemp\b': ('Hemp', 'gid://shopify/TaxonomyValue/1042'),
            r'(?i)\bjute\b': ('Jute', 'gid://shopify/TaxonomyValue/613'),
            r'(?i)\blatex\b': ('Latex', 'gid://shopify/TaxonomyValue/16987'),
            r'(?i)\bleather\b': ('Leather', 'gid://shopify/TaxonomyValue/16988'),
            r'(?i)\blinen\b': ('Linen', 'gid://shopify/TaxonomyValue/16989'),
            r'(?i)\blycra\b': ('Lycra', 'gid://shopify/TaxonomyValue/1007'),
            r'(?i)\blyocell\b': ('Lyocell', 'gid://shopify/TaxonomyValue/50'),
            r'(?i)\bmerino\b': ('Merino', 'gid://shopify/TaxonomyValue/16890'),
            r'(?i)\bmesh\b': ('Mesh', 'gid://shopify/TaxonomyValue/600'),
            r'(?i)\bmodal\b': ('Modal', 'gid://shopify/TaxonomyValue/57'),
            r'(?i)\bmohair\b': ('Mohair', 'gid://shopify/TaxonomyValue/983'),
            r'(?i)\bneoprene\b': ('Neoprene', 'gid://shopify/TaxonomyValue/566'),
            r'(?i)\bnylon\b': ('Nylon', 'gid://shopify/TaxonomyValue/16990'),
            r'(?i)\bplastic\b': ('Plastic', 'gid://shopify/TaxonomyValue/16991'),
            r'(?i)\bplush\b': ('Plush', 'gid://shopify/TaxonomyValue/16992'),
            r'(?i)\bpolyester\b': ('Polyester', 'gid://shopify/TaxonomyValue/16993'),
            r'(?i)\brattan\b': ('Rattan', 'gid://shopify/TaxonomyValue/16994'),
            r'(?i)\brayon\b': ('Rayon', 'gid://shopify/TaxonomyValue/22664'),
            r'(?i)\brubber\b': ('Rubber', 'gid://shopify/TaxonomyValue/16995'),
            r'(?i)\bsatin\b': ('Satin', 'gid://shopify/TaxonomyValue/16996'),
            r'(?i)\bsherpa\b': ('Sherpa', 'gid://shopify/TaxonomyValue/608'),
            r'(?i)\bsilk\b': ('Silk', 'gid://shopify/TaxonomyValue/16997'),
            r'(?i)\bsuede\b': ('Suede', 'gid://shopify/TaxonomyValue/561'),
            r'(?i)\bsynthetic\b': ('Synthetic', 'gid://shopify/TaxonomyValue/62'),
            r'(?i)\bterrycloth\b': ('Terrycloth', 'gid://shopify/TaxonomyValue/1019'),
            r'(?i)\btweed\b': ('Tweed', 'gid://shopify/TaxonomyValue/850'),
            r'(?i)\btwill\b': ('Twill', 'gid://shopify/TaxonomyValue/565'),
            r'(?i)\bvelour\b': ('Velour', 'gid://shopify/TaxonomyValue/564'),
            r'(?i)\bvelvet\b': ('Velvet', 'gid://shopify/TaxonomyValue/563'),
            r'(?i)\bvinyl\b': ('Vinyl', 'gid://shopify/TaxonomyValue/16998'),
            r'(?i)\bviscose\b': ('Viscose', 'gid://shopify/TaxonomyValue/55'),
            r'(?i)\bwool\b': ('Wool', 'gid://shopify/TaxonomyValue/16999'),
        }

    def extract_fabric_composition(self, body_html: str) -> List[Dict[str, str]]:
        """Extract fabric composition from product description HTML"""
        if not body_html:
            return []

        # Parse HTML
        soup = BeautifulSoup(body_html, 'html.parser')
        
        # Look for material composition in list items
        compositions = []
        material_line = None
        
        # First try to find explicit material composition line
        for li in soup.find_all('li'):
            text = li.get_text().strip().lower()
            if 'material composition' in text or 'fabric composition' in text:
                material_line = text
                break
        
        if material_line:
            # Extract percentages and materials
            matches = re.findall(r'(\d+)%\s*([a-zA-Z\s-]+)', material_line)
            for percentage, material in matches:
                material = material.strip()
                normalized = self.normalize_fabric(material)
                if normalized:
                    compositions.append({
                        'fabric': normalized[0],
                        'percentage': int(percentage),
                        'taxonomy_id': normalized[1]
                    })
        else:
            # Fallback to scanning full text for fabric mentions
            text = soup.get_text().lower()
            for pattern, (fabric, taxonomy_id) in self.fabric_mappings.items():
                if re.search(pattern, text):
                    # Try to find percentage near the fabric mention
                    match = re.search(rf'(\d+)%\s*{pattern}', text)
                    percentage = int(match.group(1)) if match else None
                    
                    compositions.append({
                        'fabric': fabric,
                        'percentage': percentage,
                        'taxonomy_id': taxonomy_id
                    })
        
        return compositions

    def normalize_fabric(self, fabric: str) -> Optional[tuple]:
        """Normalize fabric name to standard taxonomy"""
        fabric = fabric.strip().lower()
        
        for pattern, (standard_name, taxonomy_id) in self.fabric_mappings.items():
            if re.search(pattern, fabric):
                return (standard_name, taxonomy_id)
        
        return None

def process_csv(df, output_path=None):
    """Process Matrixify CSV and normalize fabrics"""
    logger.info("Processing fabric normalization")
    
    normalizer = FabricNormalizer()
    changes = []
    
    # Group by product (using Handle as identifier)
    for handle, group in df.groupby('Handle'):
        # Get body HTML from first row
        body_html = group['Body HTML'].iloc[0]
        
        # Extract fabric composition
        compositions = normalizer.extract_fabric_composition(body_html)
        
        if compositions:
            # Create fabric attribute string
            fabric_str = ', '.join(
                f"{c['fabric']} ({c['percentage']}%)" if c['percentage'] else c['fabric']
                for c in compositions
            )
            
            # Create taxonomy ID string
            taxonomy_ids = [c['taxonomy_id'] for c in compositions]
            taxonomy_str = ', '.join(taxonomy_ids)
            
            # Update all rows for this product
            old_fabric = df.loc[df['Handle'] == handle, 'Fabric'].iloc[0]
            if old_fabric != fabric_str:
                changes.append({
                    'Handle': handle,
                    'Old Fabric': old_fabric,
                    'New Fabric': fabric_str,
                    'Taxonomy IDs': taxonomy_str
                })
                
                df.loc[df['Handle'] == handle, 'Fabric'] = fabric_str
                df.loc[df['Handle'] == handle, 'Fabric Taxonomy ID'] = taxonomy_str
    
    # Save changes report
    if changes:
        changes_df = pd.DataFrame(changes)
        report_path = Path(output_path).parent / 'reports' / 'fabric_normalization_changes.csv'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        changes_df.to_csv(report_path, index=False)
        
        logger.info(f"\nFabric Normalization Summary:")
        logger.info(f"Total products processed: {len(df['Handle'].unique())}")
        logger.info(f"Products updated: {len(changes)}")
        
    # Save normalized CSV
    if output_path:
        df.to_csv(output_path, index=False)
        logger.info(f"Saved normalized CSV to {output_path}")
    
    return df, changes 