"""
File Scanner
Scans directories for ICAD files and extracts metadata.
"""

import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

from config.settings import Settings
from core.database import DatabaseManager
from utils.file_utils import FileUtils

class FileScanner:
    """Scans directories for ICAD files and indexes them"""
    
    def __init__(self, db_manager: DatabaseManager, progress_callback: Optional[Callable] = None):
        """Initialize file scanner"""
        self.db_manager = db_manager
        self.progress_callback = progress_callback
        self.file_utils = FileUtils()
        self.should_stop = False
        
    def scan_directory(self, directory: str, recursive: bool = True) -> Dict[str, Any]:
        """Scan directory for ICAD files"""
        start_time = time.time()
        directory_path = Path(directory)
        
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not directory_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory}")
        
        # Reset stop flag
        self.should_stop = False
        
        # Find all ICAD files
        files_found = self._find_icad_files(directory_path, recursive)
        
        # Process files
        files_indexed = self._process_files(files_found)
        
        # Calculate scan duration
        scan_duration = time.time() - start_time
        
        # Add to scan history
        self.db_manager.add_scan_history(
            directory, len(files_found), files_indexed, scan_duration
        )
        
        return {
            'directory': directory,
            'files_found': len(files_found),
            'files_indexed': files_indexed,
            'scan_duration': scan_duration
        }
    
    def _find_icad_files(self, directory: Path, recursive: bool) -> List[Path]:
        """Find all ICAD files in directory"""
        files = []
        
        try:
            if recursive:
                # Use recursive glob for all subdirectories
                for pattern in [f"**/*{ext}" for ext in Settings.ICAD_EXTENSIONS]:
                    files.extend(directory.glob(pattern))
            else:
                # Only scan current directory
                for pattern in [f"*{ext}" for ext in Settings.ICAD_EXTENSIONS]:
                    files.extend(directory.glob(pattern))
            
            # Filter out files from ignored directories
            filtered_files = []
            for file_path in files:
                if self.should_stop:
                    break
                    
                # Check if file is in ignored directory
                if any(Settings.should_ignore_directory(part) for part in file_path.parts):
                    continue
                    
                # Check if file should be ignored
                if Settings.IGNORE_HIDDEN_FILES and file_path.name.startswith('.'):
                    continue
                
                filtered_files.append(file_path)
            
            return filtered_files
            
        except Exception as e:
            print(f"Error finding ICAD files: {e}")
            return []
    
    def _process_files(self, files: List[Path]) -> int:
        """Process found files and add to database"""
        files_indexed = 0
        total_files = len(files)
        
        # Process files in chunks to avoid memory issues
        chunk_size = Settings.CHUNK_SIZE
        
        for i in range(0, total_files, chunk_size):
            if self.should_stop:
                break
                
            chunk = files[i:i + chunk_size]
            
            # Process chunk with thread pool
            with ThreadPoolExecutor(max_workers=Settings.MAX_THREADS) as executor:
                future_to_file = {
                    executor.submit(self._process_single_file, file_path): file_path
                    for file_path in chunk
                }
                
                for future in as_completed(future_to_file):
                    if self.should_stop:
                        break
                        
                    file_path = future_to_file[future]
                    try:
                        success = future.result()
                        if success:
                            files_indexed += 1
                    except Exception as e:
                        print(f"Error processing file {file_path}: {e}")
                    
                    # Update progress
                    if self.progress_callback:
                        progress = (i + files_indexed) / total_files * 100
                        self.progress_callback(progress, str(file_path))
        
        return files_indexed
    
    def _process_single_file(self, file_path: Path) -> bool:
        """Process a single file and extract metadata"""
        try:
            # Get file stats
            stat = file_path.stat()
            
            # Extract metadata
            metadata = self._extract_metadata(file_path)
            
            # Create file info
            file_info = {
                'file_path': str(file_path),
                'filename': file_path.name,
                'file_size': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime),
                'created_time': datetime.fromtimestamp(stat.st_ctime),
                'file_type': file_path.suffix.lower(),
                'project_name': metadata.get('project_name', ''),
                'job_name': metadata.get('job_name', ''),
                'company_name': metadata.get('company_name', ''),
                'metadata': metadata
            }
            
            # Add to database
            return self.db_manager.add_file(file_info)
            
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            return False
    
    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from file"""
        metadata = {
            'project_name': '',
            'job_name': '',
            'company_name': '',
            'drawing_number': '',
            'revision': '',
            'title': '',
            'description': '',
            'keywords': [],
            'properties': {}
        }
        
        try:
            # Extract metadata from filename
            filename_metadata = self._extract_filename_metadata(file_path.name)
            metadata.update(filename_metadata)
            
            # Extract metadata from directory structure
            dir_metadata = self._extract_directory_metadata(file_path)
            metadata.update(dir_metadata)
            
            # Try to extract metadata from file content (for supported formats)
            if file_path.suffix.lower() in ['.dwg', '.dxf']:
                content_metadata = self._extract_file_content_metadata(file_path)
                metadata.update(content_metadata)
            
        except Exception as e:
            print(f"Error extracting metadata from {file_path}: {e}")
        
        return metadata
    
    def _extract_filename_metadata(self, filename: str) -> Dict[str, Any]:
        """Extract metadata from filename patterns"""
        metadata = {}
        
        # Common filename patterns
        patterns = [
            # Pattern: ProjectName_JobName_DrawingNumber_Rev.ext
            r'([^_]+)_([^_]+)_([^_]+)_([^_.]+)',
            # Pattern: ProjectName-JobName-DrawingNumber.ext
            r'([^-]+)-([^-]+)-([^-.]+)',
            # Pattern: CompanyName_ProjectName_DrawingNumber.ext
            r'([^_]+)_([^_]+)_([^_.]+)',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                groups = match.groups()
                if len(groups) >= 3:
                    metadata['project_name'] = groups[0].strip()
                    metadata['job_name'] = groups[1].strip()
                    metadata['drawing_number'] = groups[2].strip()
                    if len(groups) >= 4:
                        metadata['revision'] = groups[3].strip()
                break
        
        # Extract drawing number from various patterns
        if not metadata.get('drawing_number'):
            # Look for drawing number patterns
            drawing_patterns = [
                r'([A-Z]{1,3}-?\d{3,6})',  # A-123456 or ABC123456
                r'(\d{4,6})',               # 123456
                r'([A-Z]\d{2,4})',          # A123
            ]
            
            for pattern in drawing_patterns:
                match = re.search(pattern, filename)
                if match:
                    metadata['drawing_number'] = match.group(1)
                    break
        
        # Extract revision from filename
        if not metadata.get('revision'):
            rev_patterns = [
                r'[_-]?[Rr]ev?[_-]?([A-Z0-9]+)',  # Rev A, Rev1, R01
                r'[_-]?[Vv]([0-9]+)',             # V1, V01
                r'[_-]?([A-Z])$',                 # Ending with single letter
            ]
            
            for pattern in rev_patterns:
                match = re.search(pattern, filename)
                if match:
                    metadata['revision'] = match.group(1)
                    break
        
        return metadata
    
    def _extract_directory_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from directory structure"""
        metadata = {}
        
        # Get parent directories
        parts = file_path.parts
        
        # Look for common directory patterns
        for i, part in enumerate(parts):
            part_lower = part.lower()
            
            # Project directories
            if any(keyword in part_lower for keyword in ['project', 'proj', 'job']):
                if i < len(parts) - 1:
                    metadata['project_name'] = parts[i + 1]
            
            # Company directories
            if any(keyword in part_lower for keyword in ['company', 'client', 'customer']):
                if i < len(parts) - 1:
                    metadata['company_name'] = parts[i + 1]
            
            # Drawing type directories
            if any(keyword in part_lower for keyword in ['drawings', 'dwg', 'cad']):
                if i > 0:
                    metadata['project_name'] = parts[i - 1]
        
        return metadata
    
    def _extract_file_content_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from file content (basic implementation)"""
        metadata = {}
        
        try:
            # For DXF files, try to extract basic information
            if file_path.suffix.lower() == '.dxf':
                metadata.update(self._extract_dxf_metadata(file_path))
            
            # For other formats, implement specific extractors as needed
            # This is a placeholder for future implementations
            
        except Exception as e:
            print(f"Error extracting content metadata from {file_path}: {e}")
        
        return metadata
    
    def _extract_dxf_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from DXF files"""
        metadata = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(10000)  # Read first 10KB
                
                # Look for title block information
                title_patterns = [
                    r'TITLE\s*\n\s*1\s*\n\s*([^\n]+)',
                    r'PROJECT\s*\n\s*1\s*\n\s*([^\n]+)',
                    r'DRAWING\s*\n\s*1\s*\n\s*([^\n]+)',
                ]
                
                for pattern in title_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        metadata['title'] = match.group(1).strip()
                        break
                
                # Look for other metadata
                if 'COMPANY' in content:
                    match = re.search(r'COMPANY\s*\n\s*1\s*\n\s*([^\n]+)', content, re.IGNORECASE)
                    if match:
                        metadata['company_name'] = match.group(1).strip()
                
        except Exception as e:
            print(f"Error extracting DXF metadata: {e}")
        
        return metadata
    
    def stop_scanning(self):
        """Stop the current scanning operation"""
        self.should_stop = True
    
    def scan_single_file(self, file_path: str) -> bool:
        """Scan a single file and add to database"""
        try:
            path = Path(file_path)
            if not path.exists():
                return False
                
            if not Settings.is_icad_file(file_path):
                return False
                
            return self._process_single_file(path)
            
        except Exception as e:
            print(f"Error scanning single file {file_path}: {e}")
            return False
    
    def rescan_missing_files(self) -> int:
        """Rescan files that are missing from the database"""
        all_files = self.db_manager.get_all_files()
        missing_files = []
        
        for file_info in all_files:
            if not Path(file_info['file_path']).exists():
                missing_files.append(file_info['file_path'])
        
        # Remove missing files from database
        for file_path in missing_files:
            self.db_manager.remove_file(file_path)
        
        return len(missing_files)