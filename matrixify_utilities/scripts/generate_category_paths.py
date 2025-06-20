#!/usr/bin/env python3

import json
from pathlib import Path
import logging
from typing import Dict, Union, List
import argparse
from collections import defaultdict

logger = logging.getLogger(__name__)

CategoryMapping = Dict[str, Union[str, Dict[str, str]]]

def load_categories(taxonomy_dir: Path) -> Dict:
    """Load categories from JSON file"""
    categories_file = taxonomy_dir / 'categories.json'
    if not categories_file.exists():
        raise FileNotFoundError(f"Categories file not found at {categories_file}")
        
    with categories_file.open() as f:
        return json.load(f).get('data', {})

def generate_category_paths(
    categories: Dict, 
    include_gid: bool = False,
    group_by_path: bool = False
) -> CategoryMapping:
    """
    Generate mapping of category names to full paths
    Only includes leaf categories under Apparel & Accessories
    
    Args:
        categories: Raw category data from taxonomy
        include_gid: Whether to include category GIDs in output
        group_by_path: Whether to group duplicate names by path
        
    Returns:
        Dictionary mapping category names to either:
        - path strings
        - or {path, gid} dicts if include_gid=True
        - or lists of such items if group_by_path=True
    """
    # First collect all matches
    matches = defaultdict(list)
    
    for cat_id, cat_data in categories.items():
        path = cat_data.get('path', '')
        
        # Only process Apparel & Accessories categories
        if not path.startswith('Apparel & Accessories'):
            continue
            
        # Skip non-leaf categories
        if cat_data.get('children', []):
            continue
            
        # Get the category name
        name = cat_data.get('name')
        if not name:
            continue
            
        # Build the category info
        if include_gid:
            cat_info = {
                'path': path,
                'gid': cat_id
            }
        else:
            cat_info = path
            
        matches[name].append(cat_info)
    
    # Process matches based on grouping preference
    category_paths = {}
    
    for name, paths in matches.items():
        if len(paths) == 1:
            # Single match - use directly
            category_paths[name] = paths[0]
        elif group_by_path:
            # Keep all paths
            category_paths[name] = sorted(paths, key=lambda x: x if isinstance(x, str) else x['path'])
        else:
            # Take most specific path
            def path_specificity(p):
                path_str = p if isinstance(p, str) else p['path']
                return len(path_str.split(' > '))
            category_paths[name] = max(paths, key=path_specificity)
            
            if len(paths) > 1:
                logger.warning(
                    f"Multiple paths found for '{name}', using most specific:\n" +
                    "\n".join(f"  - {p if isinstance(p, str) else p['path']}" for p in paths)
                )
    
    return dict(sorted(category_paths.items()))

def format_as_python(paths: CategoryMapping) -> str:
    """Format the dictionary as Python code"""
    lines = ['CATEGORY_PATHS = {']
    
    # Get max length for alignment
    max_key_length = max(len(key) for key in paths.keys())
    
    for key, value in paths.items():
        # Pad the key for alignment
        padded_key = f'"{key}"'
        padded_key = padded_key.ljust(max_key_length + 2)
        
        if isinstance(value, list):
            # Multiple paths
            lines.append(f'    {padded_key}: [')
            for path in value:
                if isinstance(path, dict):
                    lines.append(f'        {{"path": "{path["path"]}", "gid": "{path["gid"]}"}},')
                else:
                    lines.append(f'        "{path}",')
            lines.append('    ],')
        elif isinstance(value, dict):
            # Single path with GID
            lines.append(f'    {padded_key}: {{"path": "{value["path"]}", "gid": "{value["gid"]}"}},')
        else:
            # Simple path string
            lines.append(f'    {padded_key}: "{value}",')
    
    lines.append('}')
    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser(description='Generate category paths dictionary from taxonomy data')
    parser.add_argument('--taxonomy-dir', type=Path, 
                       default=Path(__file__).parent.parent / 'taxonomy_data',
                       help='Directory containing taxonomy JSON files')
    parser.add_argument('--output', type=Path,
                       help='Output file path (optional, defaults to stdout)')
    parser.add_argument('--format', choices=['python', 'json'], default='python',
                       help='Output format (default: python)')
    parser.add_argument('--include-gid', action='store_true',
                       help='Include category GIDs in output')
    parser.add_argument('--group-by-path', action='store_true',
                       help='Group duplicate category names by path instead of taking most specific')
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Load and process categories
        categories = load_categories(args.taxonomy_dir)
        logger.info(f"Loaded {len(categories)} categories")
        
        paths = generate_category_paths(
            categories,
            include_gid=args.include_gid,
            group_by_path=args.group_by_path
        )
        logger.info(f"Generated {len(paths)} category paths")
        
        # Format output
        if args.format == 'python':
            output = format_as_python(paths)
        else:
            output = json.dumps(paths, indent=2)
            
        # Write output
        if args.output:
            args.output.write_text(output)
            logger.info(f"Wrote output to {args.output}")
        else:
            print(output)
            
    except Exception as e:
        logger.error(f"Error generating category paths: {e}")
        raise

if __name__ == '__main__':
    main() 