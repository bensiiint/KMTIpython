"""
Database Manager
Handles SQLite database operations for storing and retrieving ICAD file information.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from config.settings import Settings

class DatabaseManager:
    """Manages SQLite database operations for ICAD files"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager"""
        self.db_path = db_path or Settings.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create files table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    file_size INTEGER,
                    modified_time TIMESTAMP,
                    created_time TIMESTAMP,
                    project_name TEXT,
                    job_name TEXT,
                    company_name TEXT,
                    file_type TEXT,
                    metadata TEXT,
                    indexed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create search index
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_filename ON files(filename)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_project ON files(project_name)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_job ON files(job_name)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_company ON files(company_name)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_file_type ON files(file_type)
            ''')
            
            # Create scan_history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    directory_path TEXT NOT NULL,
                    scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    files_found INTEGER,
                    files_indexed INTEGER,
                    scan_duration REAL
                )
            ''')
            
            conn.commit()
    
    def add_file(self, file_info: Dict[str, Any]) -> bool:
        """Add or update a file in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO files (
                        file_path, filename, file_size, modified_time, created_time,
                        project_name, job_name, company_name, file_type, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file_info['file_path'],
                    file_info['filename'],
                    file_info.get('file_size', 0),
                    file_info.get('modified_time'),
                    file_info.get('created_time'),
                    file_info.get('project_name', ''),
                    file_info.get('job_name', ''),
                    file_info.get('company_name', ''),
                    file_info.get('file_type', ''),
                    json.dumps(file_info.get('metadata', {}))
                ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding file to database: {e}")
            return False
    
    def remove_file(self, file_path: str) -> bool:
        """Remove a file from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM files WHERE file_path = ?', (file_path,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error removing file from database: {e}")
            return False
    
    def get_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get a file from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM files WHERE file_path = ?', (file_path,))
                row = cursor.fetchone()
                
                if row:
                    file_info = dict(row)
                    # Parse metadata JSON
                    if file_info['metadata']:
                        file_info['metadata'] = json.loads(file_info['metadata'])
                    return file_info
                return None
        except Exception as e:
            print(f"Error getting file from database: {e}")
            return None
    
    def search_files(self, query: str = '', filter_type: str = 'All', limit: int = None) -> List[Dict[str, Any]]:
        """Search files in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Build search query
                where_conditions = []
                params = []
                
                if query:
                    if filter_type == 'Filename':
                        where_conditions.append('filename LIKE ?')
                        params.append(f'%{query}%')
                    elif filter_type == 'Project':
                        where_conditions.append('project_name LIKE ?')
                        params.append(f'%{query}%')
                    elif filter_type == 'Job':
                        where_conditions.append('job_name LIKE ?')
                        params.append(f'%{query}%')
                    elif filter_type == 'Company':
                        where_conditions.append('company_name LIKE ?')
                        params.append(f'%{query}%')
                    else:  # All
                        where_conditions.append('''
                            (filename LIKE ? OR 
                             project_name LIKE ? OR 
                             job_name LIKE ? OR 
                             company_name LIKE ?)
                        ''')
                        params.extend([f'%{query}%'] * 4)
                
                # Build SQL query
                sql = 'SELECT * FROM files'
                if where_conditions:
                    sql += ' WHERE ' + ' AND '.join(where_conditions)
                sql += ' ORDER BY filename ASC'
                
                if limit:
                    sql += f' LIMIT {limit}'
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                results = []
                for row in rows:
                    file_info = dict(row)
                    # Parse metadata JSON
                    if file_info['metadata']:
                        try:
                            file_info['metadata'] = json.loads(file_info['metadata'])
                        except:
                            file_info['metadata'] = {}
                    results.append(file_info)
                
                return results
        except Exception as e:
            print(f"Error searching files: {e}")
            return []
    
    def get_all_files(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get all files from the database"""
        return self.search_files('', 'All', limit)
    
    def get_file_count(self) -> int:
        """Get total number of files in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM files')
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"Error getting file count: {e}")
            return 0
    
    def has_files(self) -> bool:
        """Check if database has any files"""
        return self.get_file_count() > 0
    
    def clear_database(self) -> bool:
        """Clear all files from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM files')
                conn.commit()
                return True
        except Exception as e:
            print(f"Error clearing database: {e}")
            return False
    
    def add_scan_history(self, directory_path: str, files_found: int, files_indexed: int, scan_duration: float):
        """Add scan history entry"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO scan_history (directory_path, files_found, files_indexed, scan_duration)
                    VALUES (?, ?, ?, ?)
                ''', (directory_path, files_found, files_indexed, scan_duration))
                conn.commit()
        except Exception as e:
            print(f"Error adding scan history: {e}")
    
    def get_scan_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get scan history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM scan_history 
                    ORDER BY scan_time DESC 
                    LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting scan history: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total files
                cursor.execute('SELECT COUNT(*) FROM files')
                total_files = cursor.fetchone()[0]
                
                # Files by type
                cursor.execute('''
                    SELECT file_type, COUNT(*) as count 
                    FROM files 
                    GROUP BY file_type 
                    ORDER BY count DESC
                ''')
                files_by_type = dict(cursor.fetchall())
                
                # Recent files
                cursor.execute('''
                    SELECT COUNT(*) FROM files 
                    WHERE indexed_time > datetime('now', '-7 days')
                ''')
                recent_files = cursor.fetchone()[0]
                
                # Total size
                cursor.execute('SELECT SUM(file_size) FROM files')
                total_size = cursor.fetchone()[0] or 0
                
                return {
                    'total_files': total_files,
                    'files_by_type': files_by_type,
                    'recent_files': recent_files,
                    'total_size': total_size
                }
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}
    
    def cleanup_missing_files(self) -> int:
        """Remove database entries for files that no longer exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, file_path FROM files')
                files = cursor.fetchall()
                
                removed_count = 0
                for file_id, file_path in files:
                    if not Path(file_path).exists():
                        cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
                        removed_count += 1
                
                conn.commit()
                return removed_count
        except Exception as e:
            print(f"Error cleaning up missing files: {e}")
            return 0