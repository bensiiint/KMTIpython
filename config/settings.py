"""
Application Settings and Configuration
Contains constants and configuration values for the ICAD File Manager.
"""

import os
from pathlib import Path

class Settings:
    """Application settings and constants"""
    
    # Application Info
    APP_NAME = "ICD File Manager"
    APP_VERSION = "1.0.0"
    APP_AUTHOR = "Engineering Team"
    
    # File Extensions - Only .icd files
    ICAD_EXTENSIONS = ['.icd']
    
    # Database Settings
    DB_NAME = "icad_files.db"
    DB_PATH = Path(__file__).parent.parent / "data" / DB_NAME
    
    # UI Settings
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    MIN_WINDOW_WIDTH = 800
    MIN_WINDOW_HEIGHT = 600
    
    # Search Settings
    SEARCH_DELAY_MS = 300  # Delay before performing search
    MAX_SEARCH_RESULTS = 1000
    
    # File Preview Settings
    PREVIEW_IMAGE_SIZE = (400, 300)
    SUPPORTED_IMAGE_FORMATS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
    
    # Scanning Settings
    SCAN_RECURSIVE = True
    IGNORE_HIDDEN_FILES = True
    IGNORE_DIRECTORIES = ['.git', '__pycache__', '.vscode', '.idea', 'node_modules']
    
    # Performance Settings
    CHUNK_SIZE = 1000  # Number of files to process at once
    MAX_THREADS = 4    # Maximum number of worker threads
    
    # Colors and Themes
    COLORS = {
        'primary': '#2563eb',
        'secondary': '#64748b',
        'success': '#10b981',
        'warning': '#f59e0b',
        'error': '#ef4444',
        'background': '#f8fafc',
        'surface': '#ffffff',
        'text': '#1e293b'
    }
    
    @classmethod
    def get_data_dir(cls):
        """Get the data directory path"""
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        return data_dir
    
    @classmethod
    def get_assets_dir(cls):
        """Get the assets directory path"""
        return Path(__file__).parent.parent / "assets"
    
    @classmethod
    def get_config_path(cls):
        """Get user configuration file path"""
        config_dir = Path.home() / ".icad_file_manager"
        config_dir.mkdir(exist_ok=True)
        return config_dir / "config.json"
    
    @classmethod
    def is_icad_file(cls, file_path):
        """Check if file is a .icd file based on extension"""
        return Path(file_path).suffix.lower() in cls.ICAD_EXTENSIONS
    
    @classmethod
    def should_ignore_directory(cls, dir_name):
        """Check if directory should be ignored during scanning"""
        return dir_name.startswith('.') or dir_name in cls.IGNORE_DIRECTORIES