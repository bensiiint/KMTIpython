"""
Search Engine
Provides advanced search functionality for ICAD files.
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from config.settings import Settings
from core.database import DatabaseManager

class SearchEngine:
    """Advanced search engine for ICAD files"""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize search engine"""
        self.db_manager = db_manager
        
    def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform advanced search with filters
        
        Args:
            query: Search query string
            filters: Dictionary of filters to apply
        
        Returns:
            List of matching files
        """
        if not query.strip() and not filters:
            return self.db_manager.get_all_files(Settings.MAX_SEARCH_RESULTS)
        
        # Parse search query
        search_terms = self._parse_query(query)
        
        # Apply filters
        results = self._search_with_filters(search_terms, filters or {})
        
        # Sort results by relevance
        results = self._sort_by_relevance(results, query)
        
        return results[:Settings.MAX_SEARCH_RESULTS]
    
    def quick_search(self, query: str, search_type: str = 'All') -> List[Dict[str, Any]]:
        """
        Perform quick search (used by search widget)
        
        Args:
            query: Search query string
            search_type: Type of search ('All', 'Filename', 'Project', 'Job', 'Company')
        
        Returns:
            List of matching files
        """
        return self.db_manager.search_files(query, search_type, Settings.MAX_SEARCH_RESULTS)
    
    def _parse_query(self, query: str) -> Dict[str, List[str]]:
        """Parse search query into terms and operators"""
        terms = {
            'include': [],
            'exclude': [],
            'exact': [],
            'wildcard': []
        }
        
        # Split query into tokens
        tokens = re.findall(r'[^\s"]+|"[^"]*"', query)
        
        for token in tokens:
            token = token.strip()
            if not token:
                continue
                
            # Exclude terms (prefixed with -)
            if token.startswith('-'):
                terms['exclude'].append(token[1:])
            # Exact phrases (quoted)
            elif token.startswith('"') and token.endswith('"'):
                terms['exact'].append(token[1:-1])
            # Wildcard terms (containing * or ?)
            elif '*' in token or '?' in token:
                terms['wildcard'].append(token)
            # Regular include terms
            else:
                terms['include'].append(token)
        
        return terms
    
    def _search_with_filters(self, search_terms: Dict[str, List[str]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search with advanced filters"""
        # Start with all files
        results = self.db_manager.get_all_files()
        
        # Apply text search
        if any(search_terms.values()):
            results = self._apply_text_search(results, search_terms)
        
        # Apply filters
        if filters:
            results = self._apply_filters(results, filters)
        
        return results
    
    def _apply_text_search(self, files: List[Dict[str, Any]], search_terms: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Apply text search to files"""
        filtered_files = []
        
        for file_info in files:
            # Create searchable text
            searchable_text = self._create_searchable_text(file_info)
            
            # Check if file matches search terms
            if self._matches_search_terms(searchable_text, search_terms):
                filtered_files.append(file_info)
        
        return filtered_files
    
    def _create_searchable_text(self, file_info: Dict[str, Any]) -> str:
        """Create searchable text from file information"""
        text_parts = [
            file_info.get('filename', ''),
            file_info.get('project_name', ''),
            file_info.get('job_name', ''),
            file_info.get('company_name', ''),
            file_info.get('file_type', ''),
        ]
        
        # Add metadata if available
        metadata = file_info.get('metadata', {})
        if isinstance(metadata, dict):
            text_parts.extend([
                metadata.get('drawing_number', ''),
                metadata.get('revision', ''),
                metadata.get('title', ''),
                metadata.get('description', ''),
                ' '.join(metadata.get('keywords', []))
            ])
        
        return ' '.join(str(part).lower() for part in text_parts if part)
    
    def _matches_search_terms(self, text: str, search_terms: Dict[str, List[str]]) -> bool:
        """Check if text matches search terms"""
        # Check exclude terms first
        for term in search_terms['exclude']:
            if term.lower() in text:
                return False
        
        # Check include terms
        for term in search_terms['include']:
            if term.lower() not in text:
                return False
        
        # Check exact phrases
        for phrase in search_terms['exact']:
            if phrase.lower() not in text:
                return False
        
        # Check wildcard terms
        for pattern in search_terms['wildcard']:
            regex_pattern = pattern.replace('*', '.*').replace('?', '.')
            if not re.search(regex_pattern.lower(), text):
                return False
        
        return True
    
    def _apply_filters(self, files: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply various filters to files"""
        filtered_files = files
        
        # File type filter
        if filters.get('file_types'):
            file_types = [ft.lower() for ft in filters['file_types']]
            filtered_files = [f for f in filtered_files if f.get('file_type', '').lower() in file_types]
        
        # Date range filter
        if filters.get('date_from') or filters.get('date_to'):
            filtered_files = self._filter_by_date(filtered_files, filters.get('date_from'), filters.get('date_to'))
        
        # Size range filter
        if filters.get('size_min') or filters.get('size_max'):
            filtered_files = self._filter_by_size(filtered_files, filters.get('size_min'), filters.get('size_max'))
        
        # Project filter
        if filters.get('projects'):
            projects = [p.lower() for p in filters['projects']]
            filtered_files = [f for f in filtered_files if f.get('project_name', '').lower() in projects]
        
        # Company filter
        if filters.get('companies'):
            companies = [c.lower() for c in filters['companies']]
            filtered_files = [f for f in filtered_files if f.get('company_name', '').lower() in companies]
        
        return filtered_files
    
    def _filter_by_date(self, files: List[Dict[str, Any]], date_from: Optional[datetime], date_to: Optional[datetime]) -> List[Dict[str, Any]]:
        """Filter files by date range"""
        filtered_files = []
        
        for file_info in files:
            file_date = file_info.get('modified_time')
            if isinstance(file_date, str):
                try:
                    file_date = datetime.fromisoformat(file_date)
                except:
                    continue
            
            if not isinstance(file_date, datetime):
                continue
            
            # Check date range
            if date_from and file_date < date_from:
                continue
            if date_to and file_date > date_to:
                continue
            
            filtered_files.append(file_info)
        
        return filtered_files
    
    def _filter_by_size(self, files: List[Dict[str, Any]], size_min: Optional[int], size_max: Optional[int]) -> List[Dict[str, Any]]:
        """Filter files by size range"""
        filtered_files = []
        
        for file_info in files:
            file_size = file_info.get('file_size', 0)
            
            # Check size range
            if size_min and file_size < size_min:
                continue
            if size_max and file_size > size_max:
                continue
            
            filtered_files.append(file_info)
        
        return filtered_files
    
    def _sort_by_relevance(self, files: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Sort files by relevance to query"""
        if not query.strip():
            return files
        
        query_lower = query.lower()
        
        def relevance_score(file_info):
            score = 0
            
            # Filename match (highest priority)
            filename = file_info.get('filename', '').lower()
            if query_lower in filename:
                if filename.startswith(query_lower):
                    score += 100
                elif filename.endswith(query_lower):
                    score += 50
                else:
                    score += 25
            
            # Project name match
            project = file_info.get('project_name', '').lower()
            if query_lower in project:
                score += 20
            
            # Job name match
            job = file_info.get('job_name', '').lower()
            if query_lower in job:
                score += 15
            
            # Company name match
            company = file_info.get('company_name', '').lower()
            if query_lower in company:
                score += 10
            
            # Metadata match
            metadata = file_info.get('metadata', {})
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    if isinstance(value, str) and query_lower in value.lower():
                        score += 5
            
            # Recent files get slight boost
            modified_time = file_info.get('modified_time')
            if isinstance(modified_time, str):
                try:
                    modified_time = datetime.fromisoformat(modified_time)
                except:
                    modified_time = None
            
            if isinstance(modified_time, datetime):
                days_old = (datetime.now() - modified_time).days
                if days_old < 7:
                    score += 5
                elif days_old < 30:
                    score += 2
            
            return score
        
        return sorted(files, key=relevance_score, reverse=True)
    
    def get_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on query"""
        if not query.strip():
            return []
        
        suggestions = set()
        query_lower = query.lower()
        
        # Get all files
        files = self.db_manager.get_all_files()
        
        for file_info in files:
            # Add filename suggestions
            filename = file_info.get('filename', '')
            if query_lower in filename.lower():
                suggestions.add(filename)
            
            # Add project suggestions
            project = file_info.get('project_name', '')
            if project and query_lower in project.lower():
                suggestions.add(project)
            
            # Add job suggestions
            job = file_info.get('job_name', '')
            if job and query_lower in job.lower():
                suggestions.add(job)
            
            # Add company suggestions
            company = file_info.get('company_name', '')
            if company and query_lower in company.lower():
                suggestions.add(company)
        
        # Sort suggestions by relevance
        suggestions_list = list(suggestions)
        suggestions_list.sort(key=lambda x: (
            0 if x.lower().startswith(query_lower) else 1,
            len(x),
            x.lower()
        ))
        
        return suggestions_list[:limit]
    
    def get_facets(self) -> Dict[str, List[str]]:
        """Get facets for advanced search"""
        facets = {
            'file_types': [],
            'projects': [],
            'companies': [],
            'jobs': []
        }
        
        files = self.db_manager.get_all_files()
        
        for file_info in files:
            # File types
            file_type = file_info.get('file_type', '')
            if file_type and file_type not in facets['file_types']:
                facets['file_types'].append(file_type)
            
            # Projects
            project = file_info.get('project_name', '')
            if project and project not in facets['projects']:
                facets['projects'].append(project)
            
            # Companies
            company = file_info.get('company_name', '')
            if company and company not in facets['companies']:
                facets['companies'].append(company)
            
            # Jobs
            job = file_info.get('job_name', '')
            if job and job not in facets['jobs']:
                facets['jobs'].append(job)
        
        # Sort facets
        for key in facets:
            facets[key].sort()
        
        return facets
    
    def get_recent_searches(self, limit: int = 10) -> List[str]:
        """Get recent search queries (placeholder for future implementation)"""
        # This would typically be stored in a separate table or user preferences
        return []
    
    def save_search(self, query: str, filters: Dict[str, Any]) -> bool:
        """Save search query for future use (placeholder)"""
        # This would typically save to a user preferences file or database
        return True