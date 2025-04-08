from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open('matrixify_utilities/api/requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="matrixify_utilities",
    version="0.1.0",
    description="Utilities for managing Shopify product data with Matrixify",
    author="Shane",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'test-clothing=matrixify_utilities.scripts.test_clothing_update:main',
            'search-categories=matrixify_utilities.scripts.search_categories:main',
            'explore-mappings=matrixify_utilities.scripts.explore_mappings:main',
            'manage-categories=matrixify_utilities.scripts.manage_product_category:main',
            'test-colors=matrixify_utilities.scripts.test_color_normalization:main',
            'print-taxonomy=matrixify_utilities.scripts.print_taxonomy_structure:main',
        ],
    },
    package_data={
        'matrixify_utilities': [
            'api/requirements.txt',
            'taxonomy_data/*.json',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
) 