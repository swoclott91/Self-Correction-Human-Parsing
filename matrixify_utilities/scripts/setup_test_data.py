from pathlib import Path
import shutil

def setup_test_directories():
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Create required directories
    directories = [
        'data/exports',
        'data/intermediate',
        'data/final'
    ]
    
    for dir_path in directories:
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {full_path}")
    
    # Copy test CSV to exports directory
    test_csv = project_root / 'tests/test_data/sample csv matrixify/products and variants.csv'
    export_csv = project_root / 'data/exports/products and variants.csv'
    
    if test_csv.exists():
        shutil.copy2(test_csv, export_csv)
        print(f"\nCopied test CSV to: {export_csv}")
    else:
        print(f"\nWarning: Test CSV not found at {test_csv}")

if __name__ == '__main__':
    setup_test_directories() 