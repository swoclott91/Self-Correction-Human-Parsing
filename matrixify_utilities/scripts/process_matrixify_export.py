import logging
from pathlib import Path
import sys
from typing import Optional
import pandas as pd
import psutil
import ctypes
from contextlib import contextmanager

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Update imports to use the correct module names and functions
from scripts.normalize_categories import process_csv as process_categories
from scripts.normalize_sizes import process_csv as process_sizes
from scripts.normalize_colors import process_colors
from scripts.validate_csv_integrity import validate_csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(project_root / 'logs/processing.log')
    ]
)
logger = logging.getLogger(__name__)

@contextmanager
def prevent_sleep():
    """Prevent system sleep during processing"""
    if sys.platform == 'win32':
        try:
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            # Prevent system sleep
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            logger.info("Sleep prevention enabled")
            yield
        finally:
            # Allow system sleep
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            logger.info("Sleep prevention disabled")
    else:
        yield  # On non-Windows systems, just yield

def check_storage_requirements(input_file: str, min_required_gb: float = 15.0):
    """Check if enough storage is available"""
    try:
        # Get number of products
        df = pd.read_csv(input_file)
        num_products = len(df['Handle'].unique())
        num_variants = len(df)
        
        # Estimate storage needs
        estimated_gb = (num_variants * 2) / 1024  # 2MB per variant image
        
        # Check available space
        free_space_gb = psutil.disk_usage('.').free / (1024**3)
        
        logger.info(f"Storage Analysis:")
        logger.info(f"Products to process: {num_products}")
        logger.info(f"Total variants: {num_variants}")
        logger.info(f"Estimated storage needed: {estimated_gb:.1f}GB")
        logger.info(f"Available storage: {free_space_gb:.1f}GB")
        
        if free_space_gb < min_required_gb:
            raise RuntimeError(
                f"Insufficient storage space. Need {min_required_gb}GB, "
                f"but only {free_space_gb:.1f}GB available"
            )
            
        if free_space_gb < estimated_gb * 1.5:  # 50% buffer
            logger.warning(
                f"Storage space is tight. Recommended to have at least "
                f"{estimated_gb * 1.5:.1f}GB available"
            )
            
    except Exception as e:
        logger.error(f"Error checking storage: {e}")
        raise

def process_matrixify_export(
    input_file: str,
    output_dir: Optional[str] = None,
    skip_steps: Optional[list] = None,
    batch_size: int = 500  # Add batch processing option
) -> str:
    """
    Process Matrixify export through all normalization steps
    
    Args:
        input_file: Path to input CSV
        output_dir: Directory for output files (default: data/final)
        skip_steps: List of steps to skip ['category', 'size', 'color']
        batch_size: Batch size for processing large files
    
    Returns:
        Path to final processed CSV
    """
    with prevent_sleep():
        try:
            # Add storage check
            check_storage_requirements(input_file)
            
            skip_steps = skip_steps or []
            
            # Setup directories
            input_path = Path(input_file)
            if not output_dir:
                output_dir = project_root / 'data/final'
            output_path = Path(output_dir)
            intermediate_dir = project_root / 'data/intermediate'
            
            for dir_path in [output_path, intermediate_dir]:
                dir_path.mkdir(parents=True, exist_ok=True)
            
            current_file = input_path
            
            # Add memory usage logging
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            logger.info(f"Initial memory usage: {initial_memory:.2f} MB")

            # 1. Category Processing
            if 'category' not in skip_steps:
                logger.info("Starting category normalization...")
                category_output = intermediate_dir / 'categories_normalized.csv'
                process_categories(str(current_file), str(category_output))
                current_file = category_output
                logger.info("Category normalization complete")
            
            # 2. Size Processing
            if 'size' not in skip_steps:
                logger.info("Starting size normalization...")
                size_output = intermediate_dir / 'sizes_normalized.csv'
                process_sizes(str(current_file), str(size_output))
                current_file = size_output
                logger.info("Size normalization complete")
            
            # 3. Color Processing
            if 'color' not in skip_steps:
                logger.info("Starting color normalization...")
                total_rows = len(pd.read_csv(current_file, nrows=1))
                if total_rows > batch_size:
                    logger.info(f"Processing {total_rows} rows in batches of {batch_size}")
                    # Process in chunks to manage memory
                    for chunk in pd.read_csv(current_file, chunksize=batch_size):
                        process_colors(chunk, str(intermediate_dir))
                else:
                    process_colors(str(current_file), str(intermediate_dir))
                current_file = intermediate_dir / 'normalized_products.csv'
                logger.info("Color normalization complete")
            
            # 4. Final Validation
            logger.info("Validating final CSV...")
            final_output = output_path / 'processed_products.csv'
            validation_result = validate_csv(str(current_file))
            
            if validation_result['is_valid']:
                # Copy to final location
                import shutil
                shutil.copy2(current_file, final_output)
                logger.info(f"Processing complete. Final file saved to {final_output}")
                return str(final_output)
            else:
                raise ValueError(f"Final validation failed: {validation_result['errors']}")
            
        except Exception as e:
            logger.error(f"Error in processing pipeline: {str(e)}", exc_info=True)
            raise

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Process Matrixify export file')
    parser.add_argument('input_file', help='Path to input CSV file')
    parser.add_argument('--output-dir', help='Output directory (optional)')
    parser.add_argument('--skip', nargs='+', choices=['category', 'size', 'color'],
                       help='Steps to skip')
    
    args = parser.parse_args()
    
    try:
        final_file = process_matrixify_export(
            args.input_file,
            args.output_dir,
            args.skip
        )
        print(f"\nProcessing complete! Final file: {final_file}")
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1) 