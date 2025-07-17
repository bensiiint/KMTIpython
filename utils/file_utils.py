"""
File Utilities
Provides utility functions for file operations and validation.
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from config.settings import Settings

class FileUtils:
    """Utility functions for file operations"""
    
    @staticmethod
    def is_valid_icad_file(file_path: str) -> bool:
        """Check if file is a valid ICAD file"""
        try:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                return False
            
            # Check if it's a file (not directory)
            if not path.is_file():
                return False
            
            # Check file extension
            if not Settings.is_icad_file(file_path):
                return False
            
            # Check if file is accessible
            if not os.access(file_path, os.R_OK):
                return False
            
            # Check minimum file size (avoid empty files)
            if path.stat().st_size < 10:
                return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def get_file_info(file_path: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive file information"""
        try:
            path = Path(file_path)
            
            if not path.exists():
                return None
            
            stat = path.stat()
            
            return {
                'path': str(path),
                'name': path.name,
                'stem': path.stem,
                'suffix': path.suffix,
                'size': stat.st_size,
                'size_human': FileUtils.format_file_size(stat.st_size),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'created': datetime.fromtimestamp(stat.st_ctime),
                'accessed': datetime.fromtimestamp(stat.st_atime),
                'is_file': path.is_file(),
                'is_directory': path.is_dir(),
                'is_readable': os.access(file_path, os.R_OK),
                'is_writable': os.access(file_path, os.W_OK),
                'parent': str(path.parent),
                'absolute_path': str(path.resolve())
            }
            
        except Exception as e:
            print(f"Error getting file info for {file_path}: {e}")
            return None
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    @staticmethod
    def get_file_hash(file_path: str, algorithm: str = 'md5') -> Optional[str]:
        """Calculate file hash"""
        try:
            if algorithm.lower() == 'md5':
                hash_obj = hashlib.md5()
            elif algorithm.lower() == 'sha1':
                hash_obj = hashlib.sha1()
            elif algorithm.lower() == 'sha256':
                hash_obj = hashlib.sha256()
            else:
                return None
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return None
    
    @staticmethod
    def safe_filename(filename: str) -> str:
        """Create a safe filename by removing invalid characters"""
        # Characters not allowed in filenames
        invalid_chars = '<>:"/\\|?*'
        
        # Replace invalid characters with underscores
        safe_name = ''.join(c if c not in invalid_chars else '_' for c in filename)
        
        # Remove leading/trailing spaces and dots
        safe_name = safe_name.strip(' .')
        
        # Ensure filename is not empty
        if not safe_name:
            safe_name = 'unnamed'
        
        # Limit length
        if len(safe_name) > 255:
            safe_name = safe_name[:255]
        
        return safe_name
    
    @staticmethod
    def create_backup(file_path: str, backup_dir: Optional[str] = None) -> Optional[str]:
        """Create a backup of the file"""
        try:
            source = Path(file_path)
            
            if not source.exists():
                return None
            
            # Determine backup directory
            if backup_dir:
                backup_path = Path(backup_dir)
            else:
                backup_path = source.parent / 'backups'
            
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{source.stem}_{timestamp}{source.suffix}"
            backup_file = backup_path / backup_filename
            
            # Copy file
            shutil.copy2(source, backup_file)
            
            return str(backup_file)
            
        except Exception as e:
            print(f"Error creating backup for {file_path}: {e}")
            return None
    
    @staticmethod
    def get_directory_size(directory: str) -> int:
        """Get total size of directory and all subdirectories"""
        try:
            total_size = 0
            
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, IOError):
                        continue
            
            return total_size
            
        except Exception as e:
            print(f"Error getting directory size for {directory}: {e}")
            return 0
    
    @staticmethod
    def find_duplicates(file_paths: List[str]) -> List[List[str]]:
        """Find duplicate files based on content hash"""
        duplicates = []
        hash_map = {}
        
        for file_path in file_paths:
            if not FileUtils.is_valid_icad_file(file_path):
                continue
            
            file_hash = FileUtils.get_file_hash(file_path)
            if file_hash:
                if file_hash in hash_map:
                    hash_map[file_hash].append(file_path)
                else:
                    hash_map[file_hash] = [file_path]
        
        # Return groups with more than one file
        for file_list in hash_map.values():
            if len(file_list) > 1:
                duplicates.append(file_list)
        
        return duplicates
    
    @staticmethod
    def validate_directory(directory: str) -> Dict[str, Any]:
        """Validate directory and return status information"""
        result = {
            'valid': False,
            'exists': False,
            'readable': False,
            'writable': False,
            'is_directory': False,
            'icad_files_count': 0,
            'total_size': 0,
            'error': None
        }
        
        try:
            path = Path(directory)
            
            result['exists'] = path.exists()
            
            if not result['exists']:
                result['error'] = "Directory does not exist"
                return result
            
            result['is_directory'] = path.is_dir()
            
            if not result['is_directory']:
                result['error'] = "Path is not a directory"
                return result
            
            result['readable'] = os.access(directory, os.R_OK)
            result['writable'] = os.access(directory, os.W_OK)
            
            if not result['readable']:
                result['error'] = "Directory is not readable"
                return result
            
            # Count ICAD files
            icad_count = 0
            total_size = 0
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if FileUtils.is_valid_icad_file(file_path):
                        icad_count += 1
                        try:
                            total_size += os.path.getsize(file_path)
                        except:
                            pass
            
            result['icad_files_count'] = icad_count
            result['total_size'] = total_size
            result['valid'] = True
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    @staticmethod
    def cleanup_temp_files(temp_dir: str, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than specified age"""
        try:
            temp_path = Path(temp_dir)
            
            if not temp_path.exists():
                return 0
            
            cleaned_count = 0
            current_time = datetime.now()
            max_age = max_age_hours * 3600  # Convert to seconds
            
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    try:
                        file_age = current_time.timestamp() - file_path.stat().st_mtime
                        if file_age > max_age:
                            file_path.unlink()
                            cleaned_count += 1
                    except Exception:
                        continue
            
            return cleaned_count
            
        except Exception as e:
            print(f"Error cleaning temp files: {e}")
            return 0
    
    @staticmethod
    def get_file_type_icon(file_path: str) -> str:
        """Get icon name for file type"""
        suffix = Path(file_path).suffix.lower()
        
        icon_map = {
            '.dwg': 'dwg_icon.png',
            '.dxf': 'dxf_icon.png',
            '.icad': 'icad_icon.png',
            '.ifc': 'ifc_icon.png',
            '.step': 'step_icon.png',
            '.stp': 'step_icon.png',
        }
        
        return icon_map.get(suffix, 'file_icon.png')
    
    @staticmethod
    def extract_archive(archive_path: str, extract_to: str) -> bool:
        """Extract archive file (zip, tar, etc.)"""
        try:
            import zipfile
            import tarfile
            
            archive = Path(archive_path)
            extract_path = Path(extract_to)
            
            if not archive.exists():
                return False
            
            extract_path.mkdir(parents=True, exist_ok=True)
            
            # Handle ZIP files
            if archive.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive, 'r') as zip_file:
                    zip_file.extractall(extract_path)
                return True
            
            # Handle TAR files
            elif archive.suffix.lower() in ['.tar', '.tar.gz', '.tgz']:
                with tarfile.open(archive, 'r:*') as tar_file:
                    tar_file.extractall(extract_path)
                return True
            
            return False
            
        except Exception as e:
            print(f"Error extracting archive {archive_path}: {e}")
            return False
    
    @staticmethod
    def watch_directory(directory: str, callback) -> Optional[Any]:
        """Watch directory for changes (requires watchdog)"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class ICADFileHandler(FileSystemEventHandler):
                def on_created(self, event):
                    if not event.is_directory and Settings.is_icad_file(event.src_path):
                        callback('created', event.src_path)
                
                def on_modified(self, event):
                    if not event.is_directory and Settings.is_icad_file(event.src_path):
                        callback('modified', event.src_path)
                
                def on_deleted(self, event):
                    if not event.is_directory and Settings.is_icad_file(event.src_path):
                        callback('deleted', event.src_path)
            
            observer = Observer()
            observer.schedule(ICADFileHandler(), directory, recursive=True)
            observer.start()
            
            return observer
            
        except ImportError:
            print("watchdog library not installed. File watching disabled.")
            return None
        except Exception as e:
            print(f"Error setting up directory watcher: {e}")
            return None