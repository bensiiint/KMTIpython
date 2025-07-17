"""
Configuration Utilities
Handles user preferences and application configuration.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
from datetime import datetime
from config.settings import Settings

class ConfigUtils:
    """Utility functions for configuration management"""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration utilities"""
        self.config_file = config_file or Settings.get_config_path()
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            else:
                self._config = self._get_default_config()
                self._save_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            self._config = self._get_default_config()
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'version': Settings.APP_VERSION,
            'first_run': True,
            'last_used': datetime.now().isoformat(),
            'window': {
                'width': Settings.WINDOW_WIDTH,
                'height': Settings.WINDOW_HEIGHT,
                'x': None,
                'y': None,
                'maximized': False
            },
            'search': {
                'default_filter': 'All',
                'max_results': Settings.MAX_SEARCH_RESULTS,
                'search_delay': Settings.SEARCH_DELAY_MS,
                'show_suggestions': True,
                'save_recent_searches': True,
                'recent_searches': []
            },
            'scanning': {
                'recursive': Settings.SCAN_RECURSIVE,
                'ignore_hidden': Settings.IGNORE_HIDDEN_FILES,
                'auto_scan': False,
                'scan_on_startup': False,
                'watch_directories': True
            },
            'preview': {
                'auto_preview': True,
                'preview_size': Settings.PREVIEW_IMAGE_SIZE,
                'show_metadata': True,
                'show_file_info': True
            },
            'directories': {
                'last_scan_dir': '',
                'watched_dirs': [],
                'favorites': []
            },
            'ui': {
                'theme': 'default',
                'font_size': 9,
                'show_toolbar': True,
                'show_statusbar': True,
                'file_list_columns': ['filename', 'project', 'job', 'company', 'modified'],
                'column_widths': {}
            },
            'performance': {
                'max_threads': Settings.MAX_THREADS,
                'chunk_size': Settings.CHUNK_SIZE,
                'cache_previews': True,
                'cache_size_mb': 100
            },
            'notifications': {
                'show_scan_complete': True,
                'show_file_changes': False,
                'show_errors': True
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> bool:
        """Set configuration value"""
        try:
            keys = key.split('.')
            config = self._config
            
            # Navigate to the parent of the target key
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # Set the value
            config[keys[-1]] = value
            
            # Update last used time
            self._config['last_used'] = datetime.now().isoformat()
            
            # Save configuration
            self._save_config()
            return True
            
        except Exception as e:
            print(f"Error setting config value {key}: {e}")
            return False
    
    def update(self, updates: Dict[str, Any]) -> bool:
        """Update multiple configuration values"""
        try:
            for key, value in updates.items():
                self.set(key, value)
            return True
        except Exception as e:
            print(f"Error updating config: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults"""
        try:
            self._config = self._get_default_config()
            self._save_config()
            return True
        except Exception as e:
            print(f"Error resetting config: {e}")
            return False
    
    def backup_config(self, backup_path: Optional[str] = None) -> Optional[str]:
        """Create a backup of current configuration"""
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = self.config_file.parent / f"config_backup_{timestamp}.json"
            
            backup_path = Path(backup_path)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, default=str)
            
            return str(backup_path)
            
        except Exception as e:
            print(f"Error backing up config: {e}")
            return None
    
    def restore_config(self, backup_path: str) -> bool:
        """Restore configuration from backup"""
        try:
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                return False
            
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_config = json.load(f)
            
            self._config = backup_config
            self._save_config()
            return True
            
        except Exception as e:
            print(f"Error restoring config: {e}")
            return False
    
    def get_window_geometry(self) -> Dict[str, Any]:
        """Get window geometry settings"""
        return {
            'width': self.get('window.width', Settings.WINDOW_WIDTH),
            'height': self.get('window.height', Settings.WINDOW_HEIGHT),
            'x': self.get('window.x'),
            'y': self.get('window.y'),
            'maximized': self.get('window.maximized', False)
        }
    
    def save_window_geometry(self, width: int, height: int, x: int, y: int, maximized: bool = False):
        """Save window geometry settings"""
        self.update({
            'window.width': width,
            'window.height': height,
            'window.x': x,
            'window.y': y,
            'window.maximized': maximized
        })
    
    def add_recent_search(self, query: str, max_recent: int = 10):
        """Add search query to recent searches"""
        recent_searches = self.get('search.recent_searches', [])
        
        # Remove duplicate if exists
        if query in recent_searches:
            recent_searches.remove(query)
        
        # Add to beginning
        recent_searches.insert(0, query)
        
        # Limit to max_recent items
        recent_searches = recent_searches[:max_recent]
        
        self.set('search.recent_searches', recent_searches)
    
    def get_recent_searches(self) -> list:
        """Get recent search queries"""
        return self.get('search.recent_searches', [])
    
    def clear_recent_searches(self):
        """Clear recent search queries"""
        self.set('search.recent_searches', [])
    
    def add_favorite_directory(self, directory: str):
        """Add directory to favorites"""
        favorites = self.get('directories.favorites', [])
        
        if directory not in favorites:
            favorites.append(directory)
            self.set('directories.favorites', favorites)
    
    def remove_favorite_directory(self, directory: str):
        """Remove directory from favorites"""
        favorites = self.get('directories.favorites', [])
        
        if directory in favorites:
            favorites.remove(directory)
            self.set('directories.favorites', favorites)
    
    def get_favorite_directories(self) -> list:
        """Get favorite directories"""
        return self.get('directories.favorites', [])
    
    def add_watched_directory(self, directory: str):
        """Add directory to watch list"""
        watched = self.get('directories.watched_dirs', [])
        
        if directory not in watched:
            watched.append(directory)
            self.set('directories.watched_dirs', watched)
    
    def remove_watched_directory(self, directory: str):
        """Remove directory from watch list"""
        watched = self.get('directories.watched_dirs', [])
        
        if directory in watched:
            watched.remove(directory)
            self.set('directories.watched_dirs', watched)
    
    def get_watched_directories(self) -> list:
        """Get watched directories"""
        return self.get('directories.watched_dirs', [])
    
    def set_last_scan_directory(self, directory: str):
        """Set last scanned directory"""
        self.set('directories.last_scan_dir', directory)
    
    def get_last_scan_directory(self) -> str:
        """Get last scanned directory"""
        return self.get('directories.last_scan_dir', '')
    
    def get_ui_settings(self) -> Dict[str, Any]:
        """Get UI-related settings"""
        return {
            'theme': self.get('ui.theme', 'default'),
            'font_size': self.get('ui.font_size', 9),
            'show_toolbar': self.get('ui.show_toolbar', True),
            'show_statusbar': self.get('ui.show_statusbar', True),
            'file_list_columns': self.get('ui.file_list_columns', ['filename', 'project', 'job', 'company', 'modified']),
            'column_widths': self.get('ui.column_widths', {})
        }
    
    def save_column_widths(self, column_widths: Dict[str, int]):
        """Save column widths"""
        self.set('ui.column_widths', column_widths)
    
    def is_first_run(self) -> bool:
        """Check if this is the first run"""
        return self.get('first_run', True)
    
    def set_first_run_complete(self):
        """Mark first run as complete"""
        self.set('first_run', False)
    
    def get_performance_settings(self) -> Dict[str, Any]:
        """Get performance-related settings"""
        return {
            'max_threads': self.get('performance.max_threads', Settings.MAX_THREADS),
            'chunk_size': self.get('performance.chunk_size', Settings.CHUNK_SIZE),
            'cache_previews': self.get('performance.cache_previews', True),
            'cache_size_mb': self.get('performance.cache_size_mb', 100)
        }
    
    def export_config(self, export_path: str) -> bool:
        """Export configuration to file"""
        try:
            export_data = {
                'version': Settings.APP_VERSION,
                'export_date': datetime.now().isoformat(),
                'config': self._config
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            print(f"Error exporting config: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """Import configuration from file"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if 'config' in import_data:
                self._config = import_data['config']
                self._save_config()
                return True
            
            return False
            
        except Exception as e:
            print(f"Error importing config: {e}")
            return False
    
    def migrate_config(self, from_version: str, to_version: str) -> bool:
        """Migrate configuration from old version to new version"""
        try:
            # This is a placeholder for future version migrations
            # Each version change would have its own migration logic
            
            current_version = self.get('version', '1.0.0')
            
            if current_version != to_version:
                # Perform migration steps here
                self.set('version', to_version)
                print(f"Config migrated from {current_version} to {to_version}")
            
            return True
            
        except Exception as e:
            print(f"Error migrating config: {e}")
            return False
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return status"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check required keys
            required_keys = ['version', 'window', 'search', 'directories']
            for key in required_keys:
                if key not in self._config:
                    validation_result['errors'].append(f"Missing required key: {key}")
                    validation_result['valid'] = False
            
            # Check window settings
            window_config = self._config.get('window', {})
            if 'width' not in window_config or window_config['width'] < 400:
                validation_result['warnings'].append("Window width too small or missing")
            
            if 'height' not in window_config or window_config['height'] < 300:
                validation_result['warnings'].append("Window height too small or missing")
            
            # Check performance settings
            perf_config = self._config.get('performance', {})
            max_threads = perf_config.get('max_threads', 1)
            if max_threads < 1 or max_threads > 32:
                validation_result['warnings'].append("Invalid max_threads value")
            
            # Check directories
            watched_dirs = self._config.get('directories', {}).get('watched_dirs', [])
            for directory in watched_dirs:
                if not Path(directory).exists():
                    validation_result['warnings'].append(f"Watched directory not found: {directory}")
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Config validation error: {e}")
        
        return validation_result