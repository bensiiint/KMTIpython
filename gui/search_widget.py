"""
Search Widget
Handles search functionality and filters for ICAD files.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Callable, Optional
import re

from core.search_engine import SearchEngine
from config.settings import Settings

class SearchWidget:
    """Search widget for finding ICAD files"""
    
    def __init__(self, parent: tk.Widget, search_engine: SearchEngine, callback: Callable):
        self.parent = parent
        self.search_engine = search_engine
        self.callback = callback
        
        # Variables
        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="All")
        self.case_sensitive_var = tk.BooleanVar(value=False)
        self.regex_var = tk.BooleanVar(value=False)
        
        # Search delay timer
        self.search_timer = None
        
        # Setup UI
        self.setup_ui()
        self.setup_bindings()
        
        # Load initial data
        self.load_facets()
    
    def setup_ui(self):
        """Setup search widget UI"""
        # Main search frame
        self.search_frame = ttk.LabelFrame(self.parent, text="Search", padding=10)
        self.search_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Search entry row
        search_row = ttk.Frame(self.search_frame)
        search_row.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_row, text="Search:").pack(side=tk.LEFT)
        
        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Clear button
        self.clear_btn = ttk.Button(search_row, text="×", width=3, command=self.clear_search)
        self.clear_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Filter row
        filter_row = ttk.Frame(self.search_frame)
        filter_row.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(filter_row, text="Filter by:").pack(side=tk.LEFT)
        
        self.filter_combo = ttk.Combobox(filter_row, textvariable=self.filter_var, 
                                       values=["All", "Filename", "Project", "Job", "Company"],
                                       state="readonly", width=15)
        self.filter_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Search button
        self.search_btn = ttk.Button(filter_row, text="Search", command=self.perform_search)
        self.search_btn.pack(side=tk.RIGHT)
        
        # Advanced options frame (collapsible)
        self.setup_advanced_options()
        
        # Quick filters frame
        self.setup_quick_filters()
        
        # Recent searches
        self.setup_recent_searches()
    
    def setup_advanced_options(self):
        """Setup advanced search options"""
        # Advanced options toggle
        self.advanced_visible = tk.BooleanVar(value=False)
        
        toggle_frame = ttk.Frame(self.search_frame)
        toggle_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.advanced_btn = ttk.Button(toggle_frame, text="▼ Advanced", 
                                     command=self.toggle_advanced)
        self.advanced_btn.pack(side=tk.LEFT)
        
        # Advanced options frame
        self.advanced_frame = ttk.Frame(self.search_frame)
        # Don't pack initially - will be shown when toggled
        
        # Search options
        options_frame = ttk.Frame(self.advanced_frame)
        options_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Checkbutton(options_frame, text="Case sensitive", 
                       variable=self.case_sensitive_var,
                       command=self.perform_search).pack(side=tk.LEFT)
        
        ttk.Checkbutton(options_frame, text="Regular expressions", 
                       variable=self.regex_var,
                       command=self.perform_search).pack(side=tk.LEFT, padx=(10, 0))
        
        # File type filters
        filetype_frame = ttk.LabelFrame(self.advanced_frame, text="File Types", padding=5)
        filetype_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.filetype_vars = {}
        file_types = ['.dwg', '.dxf', '.icad', '.ifc', '.step', '.stp']
        
        for i, file_type in enumerate(file_types):
            var = tk.BooleanVar(value=True)
            self.filetype_vars[file_type] = var
            cb = ttk.Checkbutton(filetype_frame, text=file_type, variable=var,
                               command=self.perform_search)
            cb.grid(row=i//3, column=i%3, sticky=tk.W, padx=5, pady=2)
        
        # Date range filters
        date_frame = ttk.LabelFrame(self.advanced_frame, text="Date Range", padding=5)
        date_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Date from
        date_from_frame = ttk.Frame(date_frame)
        date_from_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(date_from_frame, text="From:").pack(side=tk.LEFT)
        self.date_from_entry = ttk.Entry(date_from_frame, width=12)
        self.date_from_entry.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(date_from_frame, text="(YYYY-MM-DD)").pack(side=tk.LEFT, padx=(5, 0))
        
        # Date to
        date_to_frame = ttk.Frame(date_frame)
        date_to_frame.pack(fill=tk.X)
        
        ttk.Label(date_to_frame, text="To:").pack(side=tk.LEFT)
        self.date_to_entry = ttk.Entry(date_to_frame, width=12)
        self.date_to_entry.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(date_to_frame, text="(YYYY-MM-DD)").pack(side=tk.LEFT, padx=(5, 0))
        
        # Size filters
        size_frame = ttk.LabelFrame(self.advanced_frame, text="File Size", padding=5)
        size_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Size min
        size_min_frame = ttk.Frame(size_frame)
        size_min_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(size_min_frame, text="Min size:").pack(side=tk.LEFT)
        self.size_min_entry = ttk.Entry(size_min_frame, width=10)
        self.size_min_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        self.size_min_unit = ttk.Combobox(size_min_frame, values=["B", "KB", "MB", "GB"], 
                                         state="readonly", width=5)
        self.size_min_unit.pack(side=tk.LEFT, padx=(5, 0))
        self.size_min_unit.set("KB")
        
        # Size max
        size_max_frame = ttk.Frame(size_frame)
        size_max_frame.pack(fill=tk.X)
        
        ttk.Label(size_max_frame, text="Max size:").pack(side=tk.LEFT)
        self.size_max_entry = ttk.Entry(size_max_frame, width=10)
        self.size_max_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        self.size_max_unit = ttk.Combobox(size_max_frame, values=["B", "KB", "MB", "GB"], 
                                         state="readonly", width=5)
        self.size_max_unit.pack(side=tk.LEFT, padx=(5, 0))
        self.size_max_unit.set("MB")
    
    def setup_quick_filters(self):
        """Setup quick filter buttons"""
        self.quick_frame = ttk.LabelFrame(self.search_frame, text="Quick Filters", padding=5)
        self.quick_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Recent files button
        ttk.Button(self.quick_frame, text="Recent Files", 
                  command=lambda: self.apply_quick_filter("recent")).pack(side=tk.LEFT, padx=(0, 5))
        
        # Large files button
        ttk.Button(self.quick_frame, text="Large Files", 
                  command=lambda: self.apply_quick_filter("large")).pack(side=tk.LEFT, padx=(0, 5))
        
        # Drawing files button
        ttk.Button(self.quick_frame, text="Drawings", 
                  command=lambda: self.apply_quick_filter("drawings")).pack(side=tk.LEFT, padx=(0, 5))
        
        # Clear filters button
        ttk.Button(self.quick_frame, text="Clear All", 
                  command=self.clear_all_filters).pack(side=tk.RIGHT)
    
    def setup_recent_searches(self):
        """Setup recent searches dropdown"""
        self.recent_frame = ttk.Frame(self.search_frame)
        self.recent_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(self.recent_frame, text="Recent:").pack(side=tk.LEFT)
        
        self.recent_var = tk.StringVar()
        self.recent_combo = ttk.Combobox(self.recent_frame, textvariable=self.recent_var,
                                       state="readonly", width=25)
        self.recent_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.recent_combo.bind('<<ComboboxSelected>>', self.on_recent_selected)
        
        # Load recent searches
        self.load_recent_searches()
    
    def setup_bindings(self):
        """Setup event bindings"""
        # Search on text change with delay
        self.search_entry.bind('<KeyRelease>', self.on_search_change)
        self.search_entry.bind('<Return>', lambda e: self.perform_search())
        
        # Filter change
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self.perform_search())
        
        # Advanced option changes
        self.date_from_entry.bind('<KeyRelease>', self.on_search_change)
        self.date_to_entry.bind('<KeyRelease>', self.on_search_change)
        self.size_min_entry.bind('<KeyRelease>', self.on_search_change)
        self.size_max_entry.bind('<KeyRelease>', self.on_search_change)
        
        # Focus events
        self.search_entry.bind('<FocusIn>', self.on_search_focus)
        self.search_entry.bind('<FocusOut>', self.on_search_blur)
    
    def toggle_advanced(self):
        """Toggle advanced options visibility"""
        if self.advanced_visible.get():
            self.advanced_frame.pack_forget()
            self.advanced_btn.config(text="▼ Advanced")
            self.advanced_visible.set(False)
        else:
            self.advanced_frame.pack(fill=tk.X, pady=(5, 0))
            self.advanced_btn.config(text="▲ Advanced")
            self.advanced_visible.set(True)
    
    def on_search_change(self, event=None):
        """Handle search text change with delay"""
        # Cancel previous timer
        if self.search_timer:
            self.parent.after_cancel(self.search_timer)
        
        # Set new timer
        self.search_timer = self.parent.after(Settings.SEARCH_DELAY_MS, self.perform_search)
    
    def on_search_focus(self, event=None):
        """Handle search entry focus"""
        # Show suggestions or help text
        pass
    
    def on_search_blur(self, event=None):
        """Handle search entry blur"""
        # Hide suggestions
        pass
    
    def perform_search(self):
        """Perform search based on current settings"""
        query = self.search_var.get().strip()
        filter_type = self.filter_var.get()
        
        # Build filters
        filters = self.build_filters()
        
        # Perform search
        if self.regex_var.get():
            results = self.search_with_regex(query, filters)
        else:
            if filter_type == "All" and filters:
                results = self.search_engine.search(query, filters)
            else:
                results = self.search_engine.quick_search(query, filter_type)
                # Apply additional filters
                if filters:
                    results = self.apply_filters(results, filters)
        
        # Add to recent searches
        if query:
            self.add_recent_search(query)
        
        # Call callback with results
        self.callback(results)
    
    def build_filters(self) -> Dict[str, Any]:
        """Build filters dictionary from UI"""
        filters = {}
        
        # File type filters
        if self.advanced_visible.get():
            selected_types = [ft for ft, var in self.filetype_vars.items() if var.get()]
            if selected_types and len(selected_types) < len(self.filetype_vars):
                filters['file_types'] = selected_types
        
        # Date range filters
        date_from = self.date_from_entry.get().strip()
        date_to = self.date_to_entry.get().strip()
        
        if date_from:
            try:
                from datetime import datetime
                filters['date_from'] = datetime.strptime(date_from, '%Y-%m-%d')
            except ValueError:
                pass
        
        if date_to:
            try:
                from datetime import datetime
                filters['date_to'] = datetime.strptime(date_to, '%Y-%m-%d')
            except ValueError:
                pass
        
        # Size filters
        size_min = self.size_min_entry.get().strip()
        size_max = self.size_max_entry.get().strip()
        
        if size_min:
            try:
                size_min_bytes = self.convert_size_to_bytes(float(size_min), self.size_min_unit.get())
                filters['size_min'] = size_min_bytes
            except ValueError:
                pass
        
        if size_max:
            try:
                size_max_bytes = self.convert_size_to_bytes(float(size_max), self.size_max_unit.get())
                filters['size_max'] = size_max_bytes
            except ValueError:
                pass
        
        return filters
    
    def convert_size_to_bytes(self, size: float, unit: str) -> int:
        """Convert size to bytes"""
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024
        }
        return int(size * multipliers.get(unit, 1))
    
    def search_with_regex(self, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform regex search"""
        if not query:
            return []
        
        try:
            # Compile regex pattern
            flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
            pattern = re.compile(query, flags)
            
            # Get all files
            all_files = self.search_engine.db_manager.get_all_files()
            
            # Filter by regex
            results = []
            for file_info in all_files:
                # Create searchable text
                searchable_text = self.create_searchable_text(file_info)
                
                # Check if pattern matches
                if pattern.search(searchable_text):
                    results.append(file_info)
            
            # Apply additional filters
            if filters:
                results = self.apply_filters(results, filters)
            
            return results
            
        except re.error:
            # Invalid regex, fall back to normal search
            return self.search_engine.quick_search(query, self.filter_var.get())
    
    def create_searchable_text(self, file_info: Dict[str, Any]) -> str:
        """Create searchable text from file info"""
        text_parts = [
            file_info.get('filename', ''),
            file_info.get('project_name', ''),
            file_info.get('job_name', ''),
            file_info.get('company_name', ''),
        ]
        
        text = ' '.join(str(part) for part in text_parts if part)
        return text if self.case_sensitive_var.get() else text.lower()
    
    def apply_filters(self, files: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply filters to file list"""
        filtered_files = files
        
        # File type filter
        if 'file_types' in filters:
            file_types = [ft.lower() for ft in filters['file_types']]
            filtered_files = [f for f in filtered_files if f.get('file_type', '').lower() in file_types]
        
        # Date filters
        if 'date_from' in filters or 'date_to' in filters:
            filtered_files = self.filter_by_date(filtered_files, filters)
        
        # Size filters
        if 'size_min' in filters or 'size_max' in filters:
            filtered_files = self.filter_by_size(filtered_files, filters)
        
        return filtered_files
    
    def filter_by_date(self, files: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter files by date"""
        from datetime import datetime
        
        filtered_files = []
        date_from = filters.get('date_from')
        date_to = filters.get('date_to')
        
        for file_info in files:
            file_date = file_info.get('modified_time')
            
            if isinstance(file_date, str):
                try:
                    file_date = datetime.fromisoformat(file_date.replace('Z', '+00:00'))
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
    
    def filter_by_size(self, files: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter files by size"""
        filtered_files = []
        size_min = filters.get('size_min')
        size_max = filters.get('size_max')
        
        for file_info in files:
            file_size = file_info.get('file_size', 0)
            
            # Check size range
            if size_min and file_size < size_min:
                continue
            if size_max and file_size > size_max:
                continue
            
            filtered_files.append(file_info)
        
        return filtered_files
    
    def apply_quick_filter(self, filter_type: str):
        """Apply quick filter"""
        from datetime import datetime, timedelta
        
        if filter_type == "recent":
            # Files modified in last 7 days
            week_ago = datetime.now() - timedelta(days=7)
            self.date_from_entry.delete(0, tk.END)
            self.date_from_entry.insert(0, week_ago.strftime('%Y-%m-%d'))
            
        elif filter_type == "large":
            # Files larger than 10MB
            self.size_min_entry.delete(0, tk.END)
            self.size_min_entry.insert(0, "10")
            self.size_min_unit.set("MB")
            
        elif filter_type == "drawings":
            # Only DWG and DXF files
            for file_type, var in self.filetype_vars.items():
                var.set(file_type in ['.dwg', '.dxf'])
        
        # Show advanced options if not visible
        if not self.advanced_visible.get():
            self.toggle_advanced()
        
        # Perform search
        self.perform_search()
    
    def clear_all_filters(self):
        """Clear all filters"""
        # Clear text filters
        self.search_var.set("")
        self.filter_var.set("All")
        
        # Clear advanced options
        self.case_sensitive_var.set(False)
        self.regex_var.set(False)
        
        # Clear date filters
        self.date_from_entry.delete(0, tk.END)
        self.date_to_entry.delete(0, tk.END)
        
        # Clear size filters
        self.size_min_entry.delete(0, tk.END)
        self.size_max_entry.delete(0, tk.END)
        
        # Reset file type filters
        for var in self.filetype_vars.values():
            var.set(True)
        
        # Perform search
        self.perform_search()
    
    def clear_search(self):
        """Clear search text"""
        self.search_var.set("")
        self.perform_search()
    
    def focus_search(self):
        """Focus on search entry"""
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, tk.END)
    
    def load_facets(self):
        """Load search facets from database"""
        # This would load available projects, companies, etc.
        pass
    
    def load_recent_searches(self):
        """Load recent searches"""
        # This would load from config
        recent_searches = ["drawing", "project_a", "company_x"]  # Placeholder
        self.recent_combo['values'] = recent_searches
    
    def add_recent_search(self, query: str):
        """Add search to recent searches"""
        if query and len(query) > 2:
            current_values = list(self.recent_combo['values'])
            if query in current_values:
                current_values.remove(query)
            current_values.insert(0, query)
            self.recent_combo['values'] = current_values[:10]  # Keep only last 10
    
    def on_recent_selected(self, event):
        """Handle recent search selection"""
        selected = self.recent_var.get()
        if selected:
            self.search_var.set(selected)
            self.perform_search()
    
    def get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions"""
        return self.search_engine.get_suggestions(query)
    
    def save_search(self, name: str):
        """Save current search"""
        # TODO: Implement saved searches
        pass
    
    def load_saved_search(self, name: str):
        """Load saved search"""
        # TODO: Implement saved searches
        pass