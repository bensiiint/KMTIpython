#!/usr/bin/env python3
"""
ICAD File Manager - Setup Script
Installation script for the ICAD File Manager application.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
if (this_directory / "requirements.txt").exists():
    requirements = (this_directory / "requirements.txt").read_text().splitlines()
    # Filter out comments and empty lines
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="icad-file-manager",
    version="1.0.0",
    description="Desktop application for managing and previewing ICAD files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Engineering Team",
    author_email="engineering@company.com",
    url="https://github.com/company/icad-file-manager",
    
    # Package configuration
    packages=find_packages(),
    python_requires=">=3.8",
    
    # Dependencies
    install_requires=requirements,
    
    # Optional dependencies
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'black>=22.0.0',
            'flake8>=5.0.0',
        ],
        'docs': [
            'sphinx>=4.0.0',
            'sphinx-rtd-theme>=1.0.0',
        ],
    },
    
    # Entry points
    entry_points={
        'console_scripts': [
            'icad-manager=main:main',
        ],
        'gui_scripts': [
            'icad-manager-gui=main:main',
        ],
    },
    
    # Package data
    package_data={
        'assets': ['icons/*', 'styles/*'],
        'docs': ['*.md', '*.rst'],
    },
    
    # Include additional files
    include_package_data=True,
    
    # Metadata
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Manufacturing",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business",
        "Topic :: Scientific/Engineering",
        "Topic :: Desktop Environment :: File Managers",
        "Topic :: Multimedia :: Graphics :: Viewers",
        "Environment :: X11 Applications :: Qt",
        "Environment :: Win32 (MS Windows)",
        "Environment :: MacOS X",
    ],
    
    # Keywords
    keywords="icad, cad, file manager, engineering, drawings, preview, search",
    
    # Project URLs
    project_urls={
        'Bug Reports': 'https://github.com/company/icad-file-manager/issues',
        'Source': 'https://github.com/company/icad-file-manager',
        'Documentation': 'https://icad-file-manager.readthedocs.io/',
    },
    
    # License
    license="MIT",
    
    # Platform
    platforms=["Windows", "Linux", "macOS"],
    
    # Zip safe
    zip_safe=False,
)