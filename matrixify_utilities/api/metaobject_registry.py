import logging
from pathlib import Path
import json
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MetaobjectRegistry:
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize registry with optional cache directory"""
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / 'data' / 'cache'
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Separate caches for different types
        self.color_cache_file = self.cache_dir / 'color_metaobjects.json'
        self.palette_cache_file = self.cache_dir / 'palette_metaobjects.json'
        
        # Load caches
        self.color_cache = self._load_cache(self.color_cache_file)
        self.palette_cache = self._load_cache(self.palette_cache_file)
        
    def _load_cache(self, cache_file: Path) -> Dict:
        """Load cache from file"""
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    cache = json.load(f)
                # Validate cache freshness (7 days)
                if cache.get('last_updated'):
                    last_updated = datetime.fromisoformat(cache['last_updated'])
                    if datetime.now() - last_updated > timedelta(days=7):
                        logger.warning(f"Cache is older than 7 days: {cache_file}")
                return cache
            except Exception as e:
                logger.error(f"Error loading cache {cache_file}: {e}")
                return self._create_empty_cache()
        return self._create_empty_cache()
    
    def _create_empty_cache(self) -> Dict:
        return {
            'last_updated': None,
            'metaobjects': {},
            'definition_id': None
        }
    
    def _save_cache(self, cache: Dict, cache_file: Path):
        """Save cache to file"""
        cache['last_updated'] = datetime.now().isoformat()
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
            
    def register_color(self, handle: str, data: Dict):
        """Register a color metaobject"""
        self.color_cache['metaobjects'][handle] = data
        self._save_cache(self.color_cache, self.color_cache_file)
        
    def register_palette(self, handle: str, data: Dict):
        """Register a palette metaobject"""
        self.palette_cache['metaobjects'][handle] = data
        self._save_cache(self.palette_cache, self.palette_cache_file)
        
    def get_color(self, handle: str) -> Optional[Dict]:
        """Get color metaobject data"""
        return self.color_cache['metaobjects'].get(handle)
        
    def get_palette(self, handle: str) -> Optional[Dict]:
        """Get palette metaobject data"""
        return self.palette_cache['metaobjects'].get(handle)
        
    def set_definition_id(self, type_name: str, definition_id: str):
        """Set metaobject definition ID"""
        if type_name == 'color':
            self.color_cache['definition_id'] = definition_id
            self._save_cache(self.color_cache, self.color_cache_file)
        elif type_name == 'palette':
            self.palette_cache['definition_id'] = definition_id
            self._save_cache(self.palette_cache, self.palette_cache_file)
            
    def get_definition_id(self, type_name: str) -> Optional[str]:
        """Get metaobject definition ID"""
        if type_name == 'color':
            return self.color_cache.get('definition_id')
        elif type_name == 'palette':
            return self.palette_cache.get('definition_id')
        return None 