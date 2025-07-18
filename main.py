"""
Enhanced main.py with ICAD Screen Capture Integration
Adds automated isometric thumbnail generation to your existing ICD File Explorer
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import os
import sys
from datetime import datetime
import threading
import time
import re
from typing import List, Dict, Any, Optional

# Import the screen capture system
from icad_screen_capture import ICADScreenCapture, ThumbnailWorker

class Settings:
    """Application settings"""
    APP_NAME = "ICD File Explorer"
    APP_VERSION = "1.0.0"
    
    # Supported file extensions - Only .icd files
    ICAD_EXTENSIONS = {
        '.icd': 'ICAD Document'
    }
    
    # UI Settings
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 900
    MIN_WINDOW_WIDTH = 1000
    MIN_WINDOW_HEIGHT = 700
    
    @classmethod
    def is_supported_file(cls, file_path: str) -> bool:
        """Check if file is supported"""
        return Path(file_path).suffix.lower() in cls.ICAD_EXTENSIONS
    
    @classmethod
    def get_file_type_description(cls, file_path: str) -> str:
        """Get file type description"""
        ext = Path(file_path).suffix.lower()
        return cls.ICAD_EXTENSIONS.get(ext, 'Unknown')

class FileInfo:
    """File information container"""
    
    def __init__(self, file_path: Path):
        self.path = file_path
        self.name = file_path.name
        self.stem = file_path.stem
        self.suffix = file_path.suffix.lower()
        self.parent = file_path.parent
        
        # Get file stats
        try:
            stat = file_path.stat()
            self.size = stat.st_size
            self.modified = datetime.fromtimestamp(stat.st_mtime)
            self.created = datetime.fromtimestamp(stat.st_ctime)
        except:
            self.size = 0
            self.modified = datetime.now()
            self.created = datetime.now()
        
        # Extract metadata from filename and path
        self.project_name = self._extract_project_name()
        self.job_name = self._extract_job_name()
        self.company_name = self._extract_company_name()
        self.drawing_number = self._extract_drawing_number()
        self.revision = self._extract_revision()
    
    def _extract_project_name(self) -> str:
        """Extract project name from path/filename"""
        # Try to get from parent directory first
        parent_name = self.parent.name.upper()
        if any(keyword in parent_name for keyword in ['PROJECT', 'PROJ', 'JOB']):
            return self.parent.name
        
        # Try to get from filename
        parts = self.stem.split('_')
        if len(parts) >= 2:
            return parts[0]
        
        # Use parent directory name as fallback
        return self.parent.name
    
    def _extract_job_name(self) -> str:
        """Extract job name from filename"""
        parts = self.stem.split('_')
        if len(parts) >= 2:
            return parts[1]
        return ""
    
    def _extract_company_name(self) -> str:
        """Extract company name from filename or path"""
        # Look for company in parent directories
        for parent in self.path.parents:
            parent_name = parent.name.upper()
            if any(keyword in parent_name for keyword in ['COMPANY', 'CLIENT', 'CUSTOMER']):
                return parent.name
        
        # Try from filename
        parts = self.stem.split('_')
        if len(parts) >= 3:
            return parts[2]
        
        return ""
    
    def _extract_drawing_number(self) -> str:
        """Extract drawing number from filename"""
        # Common patterns for drawing numbers
        patterns = [
            r'([A-Z]{1,3}-?\d{3,6})',  # A-123456 or ABC123456
            r'(\d{4,6})',              # 123456
            r'([A-Z]\d{2,4})',         # A123
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.stem.upper())
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_revision(self) -> str:
        """Extract revision from filename"""
        patterns = [
            r'[_-]?[Rr]ev?[_-]?([A-Z0-9]+)',  # Rev A, Rev1, R01
            r'[_-]?[Vv]([0-9]+)',             # V1, V01
            r'[_-]?([A-Z])$',                 # Ending with single letter
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.stem)
            if match:
                return match.group(1)
        
        return ""
    
    def matches_search(self, query: str, search_type: str) -> bool:
        """Check if file matches search query"""
        if not query:
            return True
        
        query = query.lower()
        
        if search_type == "Filename":
            return query in self.name.lower()
        elif search_type == "Project":
            return query in self.project_name.lower()
        elif search_type == "Job":
            return query in self.job_name.lower()
        elif search_type == "Company":
            return query in self.company_name.lower()
        elif search_type == "Drawing":
            return query in self.drawing_number.lower()
        else:  # All
            searchable_text = f"{self.name} {self.project_name} {self.job_name} {self.company_name} {self.drawing_number}".lower()
            return query in searchable_text
    
    def format_size(self) -> str:
        """Format file size"""
        if self.size == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        size = self.size
        i = 0
        
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"

class ICADFileExplorer:
    """Main ICAD File Explorer Application with Screen Capture Thumbnails"""
    
    def __init__(self):
        self.current_folder = None
        self.all_files = []
        self.filtered_files = []
        self.selected_file = None
        self.search_timer = None
        self.scan_thread = None
        
        # Initialize screen capture system
        self.screen_capture = ICADScreenCapture()
        self.thumbnail_worker = None
        self.current_thumbnail_image = None
        
        # Setup GUI
        self.setup_gui()
        
        # Show welcome message
        self.show_welcome()
    
    def setup_gui(self):
        """Setup the main GUI"""
        # Create root window
        self.root = tk.Tk()
        self.root.title(f"{Settings.APP_NAME} v{Settings.APP_VERSION}")
        self.root.geometry(f"{Settings.WINDOW_WIDTH}x{Settings.WINDOW_HEIGHT}")
        self.root.minsize(Settings.MIN_WINDOW_WIDTH, Settings.MIN_WINDOW_HEIGHT)
        
        # Variables
        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="All")
        self.status_var = tk.StringVar(value="Select a project folder to start")
        self.progress_var = tk.DoubleVar()
        
        # Create interface
        self.create_menu()
        self.create_toolbar()
        self.create_main_content()
        self.create_status_bar()
        
        # Bindings
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.search_var.trace('w', self.on_search_change)
        
        # Keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.select_folder())
        self.root.bind('<Control-f>', lambda e: self.focus_search())
        self.root.bind('<F5>', lambda e: self.refresh_current_folder())
        self.root.bind('<Escape>', lambda e: self.clear_search())
    
    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Project Folder...", command=self.select_folder, accelerator="Ctrl+O")
        file_menu.add_command(label="Refresh", command=self.refresh_current_folder, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Clear Thumbnail Cache", command=self.clear_thumbnail_cache)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self.refresh_current_folder, accelerator="F5")
        view_menu.add_command(label="Clear Search", command=self.clear_search, accelerator="Esc")
        view_menu.add_separator()
        view_menu.add_command(label="Regenerate Thumbnail", command=self.regenerate_thumbnail)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_toolbar(self):
        """Create toolbar"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Folder selection
        ttk.Button(toolbar, text="📁 Select Project Folder", 
                  command=self.select_folder).pack(side=tk.LEFT, padx=(0, 10))
        
        # Current folder display
        self.folder_label = ttk.Label(toolbar, text="No folder selected", 
                                    font=('TkDefaultFont', 9, 'bold'))
        self.folder_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Search section
        ttk.Label(toolbar, text="🔍 Search:").pack(side=tk.LEFT, padx=(0, 5))
        
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=25)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Filter dropdown
        ttk.Label(toolbar, text="in:").pack(side=tk.LEFT, padx=(5, 5))
        
        filter_combo = ttk.Combobox(toolbar, textvariable=self.filter_var,
                                   values=["All", "Filename", "Project", "Job", "Company", "Drawing"],
                                   state="readonly", width=10)
        filter_combo.pack(side=tk.LEFT, padx=(0, 5))
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        
        # Clear search button
        ttk.Button(toolbar, text="✖", width=3, 
                  command=self.clear_search).pack(side=tk.LEFT, padx=(5, 0))
        
        # Refresh button
        ttk.Button(toolbar, text="🔄 Refresh", 
                  command=self.refresh_current_folder).pack(side=tk.RIGHT)
        
        # Progress bar (hidden initially)
        self.progress_bar = ttk.Progressbar(toolbar, mode='indeterminate')
    
    def create_main_content(self):
        """Create main content area"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Paned window for resizable panels
        self.paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel (file list)
        self.create_file_list_panel()
        
        # Right panel (preview with thumbnail)
        self.create_preview_panel()
        
        # Set initial pane sizes
        self.root.after(100, lambda: self.paned_window.sashpos(0, 900))
    
    def create_file_list_panel(self):
        """Create file list panel"""
        left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(left_frame, weight=2)
        
        # File list header
        header_frame = ttk.Frame(left_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header_frame, text="📄 Files", font=('TkDefaultFont', 10, 'bold')).pack(side=tk.LEFT)
        
        self.file_count_label = ttk.Label(header_frame, text="0 files")
        self.file_count_label.pack(side=tk.RIGHT)
        
        # File list with columns
        columns = ('name', 'project', 'job', 'company', 'type', 'size', 'modified')
        self.file_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=25)
        
        # Configure columns
        column_config = {
            'name': ('Filename', 250),
            'project': ('Project', 120),
            'job': ('Job', 100),
            'company': ('Company', 100),
            'type': ('Type', 80),
            'size': ('Size', 80),
            'modified': ('Modified', 140)
        }
        
        for col, (heading, width) in column_config.items():
            self.file_tree.heading(col, text=heading)
            self.file_tree.column(col, width=width)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        h_scrollbar = ttk.Scrollbar(left_frame, orient=tk.HORIZONTAL, command=self.file_tree.xview)
        
        self.file_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack file tree and scrollbars
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bindings
        self.file_tree.bind('<<TreeviewSelect>>', self.on_file_select)
        self.file_tree.bind('<Double-1>', self.on_file_double_click)
        self.file_tree.bind('<Return>', self.on_file_double_click)
        
        # Context menu
        self.create_context_menu()
    
    def create_context_menu(self):
        """Create right-click context menu"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open", command=self.open_selected_file)
        self.context_menu.add_command(label="Open Folder", command=self.open_selected_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Generate Thumbnail", command=self.regenerate_thumbnail)
        self.context_menu.add_command(label="Copy Path", command=self.copy_selected_path)
        self.context_menu.add_command(label="Properties", command=self.show_file_properties)
        
        # Bind right-click
        self.file_tree.bind('<Button-3>', self.show_context_menu)
    
    def create_preview_panel(self):
        """Create preview panel with thumbnail support"""
        right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(right_frame, weight=1)
        
        # Preview header
        preview_header = ttk.Frame(right_frame)
        preview_header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(preview_header, text="👁️ Preview", font=('TkDefaultFont', 10, 'bold')).pack(side=tk.LEFT)
        
        # Action buttons
        button_frame = ttk.Frame(preview_header)
        button_frame.pack(side=tk.RIGHT)
        
        self.open_btn = ttk.Button(button_frame, text="Open", command=self.open_selected_file, state=tk.DISABLED)
        self.open_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.folder_btn = ttk.Button(button_frame, text="Folder", command=self.open_selected_folder, state=tk.DISABLED)
        self.folder_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.thumbnail_btn = ttk.Button(button_frame, text="🖼️ Thumbnail", command=self.regenerate_thumbnail, state=tk.DISABLED)
        self.thumbnail_btn.pack(side=tk.LEFT)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Thumbnail tab
        self.thumbnail_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.thumbnail_frame, text="Thumbnail")
        
        # Thumbnail display area
        self.thumbnail_canvas = tk.Canvas(self.thumbnail_frame, bg='white', width=400, height=300)
        self.thumbnail_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Thumbnail status
        self.thumbnail_status = ttk.Label(self.thumbnail_frame, text="Select a file to generate thumbnail")
        self.thumbnail_status.pack(pady=5)
        
        # Progress bar for thumbnail generation
        self.thumbnail_progress = ttk.Progressbar(self.thumbnail_frame, mode='indeterminate')
        
        # Details tab
        self.details_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.details_frame, text="Details")
        
        # Details content
        self.details_text = tk.Text(self.details_frame, wrap=tk.WORD, height=20, 
                                   font=('Consolas', 9))
        details_scrollbar = ttk.Scrollbar(self.details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scrollbar.set)
        
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Initial message
        self.show_preview_message("Select a file to preview its information...")
    
    def create_status_bar(self):
        """Create status bar"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
        
        # Status label
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)
        
        # Ready indicator
        self.ready_label = ttk.Label(status_frame, text="Ready")
        self.ready_label.pack(side=tk.RIGHT)
    
    def show_welcome(self):
        """Show welcome message"""
        welcome_msg = f"""Welcome to {Settings.APP_NAME} with ICAD Thumbnails!

🎯 New Features:
• Automated isometric thumbnail generation
• Screen capture from ICAD
• Cached thumbnails for fast loading
• Real-time preview of your 3D models

🚀 Quick Start:
1. Click "📁 Select Project Folder" to choose your project folder
2. Browse and search through your .icd files instantly
3. Click on any file to generate isometric thumbnail
4. Thumbnails are cached for instant reload

🔍 Search Tips:
• Search across all file information or select specific fields
• Use the filter dropdown to search in specific areas
• Results update as you type

⌨️ Keyboard Shortcuts:
• Ctrl+O: Select folder
• Ctrl+F: Focus search
• F5: Refresh
• Esc: Clear search
• Enter: Open selected file

🖼️ Thumbnail Features:
• Automatic isometric view capture
• Fast 3-5 second generation
• Cached for instant loading
• Right-click to regenerate

📋 Supported File Types:
• .icd - ICAD Documents

Ready to see your 3D models instantly? Select a project folder to begin!"""
        
        self.show_preview_message(welcome_msg)
    
    def select_folder(self):
        """Select project folder"""
        folder = filedialog.askdirectory(title="Select Project Folder")
        if folder:
            self.current_folder = Path(folder)
            self.folder_label.config(text=f"📁 {self.current_folder.name}")
            self.scan_folder()
    
    def scan_folder(self):
        """Scan current folder for files"""
        if not self.current_folder:
            return
        
        # Show progress
        self.progress_bar.pack(side=tk.LEFT, padx=(10, 0))
        self.progress_bar.start()
        self.ready_label.config(text="Scanning...")
        self.status_var.set("Scanning folder for .icd files...")
        
        # Start scan in background thread
        if self.scan_thread and self.scan_thread.is_alive():
            return  # Already scanning
        
        self.scan_thread = threading.Thread(target=self._scan_folder_thread, daemon=True)
        self.scan_thread.start()
    
    def _scan_folder_thread(self):
        """Background thread for folder scanning"""
        try:
            files = []
            
            # Scan folder recursively
            for file_path in self.current_folder.rglob("*"):
                if file_path.is_file() and Settings.is_supported_file(str(file_path)):
                    try:
                        file_info = FileInfo(file_path)
                        files.append(file_info)
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
            
            # Sort files by name
            files.sort(key=lambda f: f.name.lower())
            
            # Update UI in main thread
            self.root.after(0, lambda: self._scan_complete(files))
            
        except Exception as e:
            self.root.after(0, lambda: self._scan_error(str(e)))
    
    def _scan_complete(self, files: List[FileInfo]):
        """Handle scan completion"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.ready_label.config(text="Ready")
        
        self.all_files = files
        self.apply_filters()
        
        count = len(files)
        self.status_var.set(f"Found {count} .icd files in {self.current_folder.name}")
        
        # Show summary in preview
        self.show_folder_summary()
    
    def _scan_error(self, error_msg: str):
        """Handle scan error"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.ready_label.config(text="Error")
        self.status_var.set(f"Error scanning folder: {error_msg}")
        messagebox.showerror("Scan Error", f"Error scanning folder: {error_msg}")
    
    def show_folder_summary(self):
        """Show folder summary in preview"""
        if not self.all_files:
            return
        
        # Count files by type
        type_counts = {}
        total_size = 0
        
        for file_info in self.all_files:
            file_type = Settings.get_file_type_description(str(file_info.path))
            type_counts[file_type] = type_counts.get(file_type, 0) + 1
            total_size += file_info.size
        
        # Check for cached thumbnails
        cached_thumbnails = 0
        for file_info in self.all_files:
            thumbnail_path = self.screen_capture.get_thumbnail_path(str(file_info.path))
            if thumbnail_path and thumbnail_path.exists():
                cached_thumbnails += 1
        
        # Format summary
        summary = f"""📁 Folder Summary: {self.current_folder.name}

📊 File Statistics:
• Total Files: {len(self.all_files):,}
• Total Size: {self._format_size(total_size)}
• Folder Path: {self.current_folder}

🖼️ Thumbnail Status:
• Cached Thumbnails: {cached_thumbnails}/{len(self.all_files)}
• Cache Directory: {self.screen_capture.cache_dir}

📋 File Types:
"""
        
        for file_type, count in sorted(type_counts.items()):
            summary += f"• {file_type}: {count:,} files\n"
        
        summary += f"""
🔍 Search Tips:
• Type in the search box to filter files
• Use the dropdown to search specific fields
• Results update as you type

💡 Next Steps:
• Search for specific files or projects
• Click on files to generate thumbnails
• Double-click to open files
• Right-click for more options

🖼️ Thumbnail Generation:
• First thumbnail takes 3-5 seconds
• Subsequent loads are instant (cached)
• Thumbnails show isometric view from ICAD
"""
        
        self.show_preview_message(summary)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        size = size_bytes
        i = 0
        
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def on_search_change(self, *args):
        """Handle search text change"""
        if self.search_timer:
            self.root.after_cancel(self.search_timer)
        self.search_timer = self.root.after(300, self.apply_filters)
    
    def apply_filters(self):
        """Apply search filters"""
        if not self.all_files:
            return
        
        query = self.search_var.get().strip()
        search_type = self.filter_var.get()
        
        # Filter files
        if query:
            self.filtered_files = [f for f in self.all_files if f.matches_search(query, search_type)]
        else:
            self.filtered_files = self.all_files.copy()
        
        # Update file list
        self.update_file_list()
        
        # Update status
        if query:
            self.status_var.set(f"Found {len(self.filtered_files)} files matching '{query}'")
        else:
            self.status_var.set(f"Showing {len(self.filtered_files)} files")
    
    def update_file_list(self):
        """Update file list display"""
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # Add filtered files
        for file_info in self.filtered_files:
            self.file_tree.insert('', 'end', values=(
                file_info.name,
                file_info.project_name,
                file_info.job_name,
                file_info.company_name,
                Settings.get_file_type_description(str(file_info.path)),
                file_info.format_size(),
                file_info.modified.strftime('%Y-%m-%d %H:%M')
            ))
        
        # Update count
        count = len(self.filtered_files)
        self.file_count_label.config(text=f"{count} file{'s' if count != 1 else ''}")
    
    def on_file_select(self, event):
        """Handle file selection"""
        selection = self.file_tree.selection()
        if selection:
            item = selection[0]
            values = self.file_tree.item(item, 'values')
            filename = values[0]
            
            # Find file info
            for file_info in self.filtered_files:
                if file_info.name == filename:
                    self.selected_file = file_info
                    self.show_file_preview(file_info)
                    self.load_thumbnail(file_info)
                    
                    # Enable buttons
                    self.open_btn.config(state=tk.NORMAL)
                    self.folder_btn.config(state=tk.NORMAL)
                    self.thumbnail_btn.config(state=tk.NORMAL)
                    break
        else:
            self.selected_file = None
            self.open_btn.config(state=tk.DISABLED)
            self.folder_btn.config(state=tk.DISABLED)
            self.thumbnail_btn.config(state=tk.DISABLED)
    
    def show_file_preview(self, file_info: FileInfo):
        """Show file preview"""
        preview_text = f"""📄 {file_info.name}

📁 Location:
• Path: {file_info.path}
• Folder: {file_info.parent.name}
• Full Path: {file_info.path}

📋 File Information:
• Type: {Settings.get_file_type_description(str(file_info.path))}
• Size: {file_info.format_size()}
• Modified: {file_info.modified.strftime('%Y-%m-%d %H:%M:%S')}
• Created: {file_info.created.strftime('%Y-%m-%d %H:%M:%S')}

🏗️ Project Information:
• Project: {file_info.project_name or 'Not detected'}
• Job: {file_info.job_name or 'Not detected'}
• Company: {file_info.company_name or 'Not detected'}
• Drawing #: {file_info.drawing_number or 'Not detected'}
• Revision: {file_info.revision or 'Not detected'}

🖼️ Thumbnail Information:
• Thumbnail: {"Cached" if self.screen_capture.get_thumbnail_path(str(file_info.path)) and self.screen_capture.get_thumbnail_path(str(file_info.path)).exists() else "Not generated"}
• Cache Directory: {self.screen_capture.cache_dir}

💡 Actions:
• Double-click to open file
• Right-click for more options
• Use "🖼️ Thumbnail" button to regenerate
• Use "Open" button to launch file
• Use "Folder" button to open containing folder
"""
        
        self.show_preview_message(preview_text)
    
    def load_thumbnail(self, file_info: FileInfo):
        """Load or generate thumbnail for file"""
        if not file_info:
            return
        
        # Clear current thumbnail
        self.thumbnail_canvas.delete("all")
        self.current_thumbnail_image = None
        
        # Check if thumbnail already exists
        thumbnail_path = self.screen_capture.get_thumbnail_path(str(file_info.path))
        
        if thumbnail_path and thumbnail_path.exists():
            # Load existing thumbnail
            self.display_thumbnail(str(thumbnail_path))
            self.thumbnail_status.config(text=f"Cached thumbnail: {file_info.name}")
        else:
            # Generate new thumbnail
            self.generate_thumbnail(file_info)
    
    def generate_thumbnail(self, file_info: FileInfo):
        """Generate thumbnail for file"""
        if not file_info:
            return
        
        # Show loading state
        self.thumbnail_canvas.delete("all")
        self.thumbnail_canvas.create_text(200, 150, text="Generating thumbnail...\n\nPlease wait 3-5 seconds", 
                                         font=('TkDefaultFont', 12), fill='gray')
        
        self.thumbnail_progress.pack(pady=10)
        self.thumbnail_progress.start()
        
        self.thumbnail_status.config(text=f"Generating thumbnail for {file_info.name}...")
        
        # Cancel any existing thumbnail generation
        if self.thumbnail_worker and self.thumbnail_worker.is_alive():
            return
        
        # Start thumbnail generation in background
        self.thumbnail_worker = ThumbnailWorker(
            str(file_info.path),
            self.screen_capture,
            self.on_thumbnail_generated
        )
        self.thumbnail_worker.start()
    
    def on_thumbnail_generated(self, thumbnail_path: str, error: str):
        """Handle thumbnail generation completion"""
        # Stop loading animation
        self.thumbnail_progress.stop()
        self.thumbnail_progress.pack_forget()
        
        if error:
            self.thumbnail_canvas.delete("all")
            self.thumbnail_canvas.create_text(200, 150, text=f"Error generating thumbnail:\n{error}", 
                                             font=('TkDefaultFont', 10), fill='red')
            self.thumbnail_status.config(text=f"Error: {error}")
        elif thumbnail_path:
            self.display_thumbnail(thumbnail_path)
            self.thumbnail_status.config(text=f"Thumbnail generated: {Path(thumbnail_path).name}")
        else:
            self.thumbnail_canvas.delete("all")
            self.thumbnail_canvas.create_text(200, 150, text="Could not generate thumbnail", 
                                             font=('TkDefaultFont', 10), fill='red')
            self.thumbnail_status.config(text="Thumbnail generation failed")
    
    def display_thumbnail(self, thumbnail_path: str):
        """Display thumbnail in canvas"""
        try:
            from PIL import Image, ImageTk
            
            # Load thumbnail
            image = Image.open(thumbnail_path)
            
            # Convert to PhotoImage
            self.current_thumbnail_image = ImageTk.PhotoImage(image)
            
            # Clear canvas and display image
            self.thumbnail_canvas.delete("all")
            
            # Center image in canvas
            canvas_width = self.thumbnail_canvas.winfo_width()
            canvas_height = self.thumbnail_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:  # Canvas is properly sized
                x = canvas_width // 2
                y = canvas_height // 2
            else:
                x = 200  # Default position
                y = 150
            
            self.thumbnail_canvas.create_image(x, y, image=self.current_thumbnail_image)
            
        except Exception as e:
            self.thumbnail_canvas.delete("all")
            self.thumbnail_canvas.create_text(200, 150, text=f"Error displaying thumbnail:\n{str(e)}", 
                                             font=('TkDefaultFont', 10), fill='red')
    
    def regenerate_thumbnail(self):
        """Regenerate thumbnail for selected file"""
        if not self.selected_file:
            return
        
        # Delete cached thumbnail
        thumbnail_path = self.screen_capture.get_thumbnail_path(str(self.selected_file.path))
        if thumbnail_path and thumbnail_path.exists():
            thumbnail_path.unlink()
        
        # Generate new thumbnail
        self.generate_thumbnail(self.selected_file)
    
    def clear_thumbnail_cache(self):
        """Clear all cached thumbnails"""
        try:
            import shutil
            if self.screen_capture.cache_dir.exists():
                shutil.rmtree(self.screen_capture.cache_dir)
                self.screen_capture.cache_dir.mkdir()
            
            messagebox.showinfo("Cache Cleared", "All cached thumbnails have been cleared.")
            
            # Refresh preview if file is selected
            if self.selected_file:
                self.load_thumbnail(self.selected_file)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear cache: {e}")
    
    def show_preview_message(self, message: str):
        """Show message in preview area"""
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, message)
        self.details_text.config(state=tk.DISABLED)
    
    def on_file_double_click(self, event):
        """Handle double-click on file"""
        self.open_selected_file()
    
    def open_selected_file(self):
        """Open selected file"""
        if not self.selected_file:
            return
        
        try:
            if self.selected_file.path.exists():
                os.startfile(str(self.selected_file.path))  # Windows
            else:
                messagebox.showwarning("File Not Found", f"File not found: {self.selected_file.path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {e}")
    
    def open_selected_folder(self):
        """Open folder containing selected file"""
        if not self.selected_file:
            return
        
        try:
            os.startfile(str(self.selected_file.parent))  # Windows
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {e}")
    
    def copy_selected_path(self):
        """Copy selected file path to clipboard"""
        if not self.selected_file:
            return
        
        self.root.clipboard_clear()
        self.root.clipboard_append(str(self.selected_file.path))
        self.status_var.set("File path copied to clipboard")
    
    def show_file_properties(self):
        """Show file properties dialog"""
        if not self.selected_file:
            return
        
        # Create properties window
        props_window = tk.Toplevel(self.root)
        props_window.title(f"Properties - {self.selected_file.name}")
        props_window.geometry("500x400")
        props_window.resizable(False, False)
        
        # File properties text
        props_text = tk.Text(props_window, wrap=tk.WORD, font=('Consolas', 9))
        props_scrollbar = ttk.Scrollbar(props_window, orient=tk.VERTICAL, command=props_text.yview)
        props_text.configure(yscrollcommand=props_scrollbar.set)
        
        # Properties content
        file_info = self.selected_file
        thumbnail_path = self.screen_capture.get_thumbnail_path(str(file_info.path))
        
        properties = f"""File Properties: {file_info.name}

General:
• Name: {file_info.name}
• Type: {Settings.get_file_type_description(str(file_info.path))}
• Size: {file_info.format_size()} ({file_info.size:,} bytes)
• Location: {file_info.parent}

Timestamps:
• Modified: {file_info.modified.strftime('%Y-%m-%d %H:%M:%S')}
• Created: {file_info.created.strftime('%Y-%m-%d %H:%M:%S')}

Project Information:
• Project: {file_info.project_name or 'Not detected'}
• Job: {file_info.job_name or 'Not detected'}
• Company: {file_info.company_name or 'Not detected'}
• Drawing Number: {file_info.drawing_number or 'Not detected'}
• Revision: {file_info.revision or 'Not detected'}

Thumbnail Information:
• Thumbnail Status: {"Available" if thumbnail_path and thumbnail_path.exists() else "Not generated"}
• Thumbnail Path: {thumbnail_path or "Not generated"}
• Cache Directory: {self.screen_capture.cache_dir}

Technical:
• Extension: {file_info.suffix}
• Stem: {file_info.stem}
• Absolute Path: {file_info.path.resolve()}
"""
        
        props_text.insert(tk.END, properties)
        props_text.config(state=tk.DISABLED)
        
        props_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        props_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # Close button
        ttk.Button(props_window, text="Close", command=props_window.destroy).pack(pady=10)
    
    def show_context_menu(self, event):
        """Show context menu"""
        # Select item under cursor
        item = self.file_tree.identify_row(event.y)
        if item:
            self.file_tree.selection_set(item)
            self.file_tree.focus(item)
            
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
    
    def focus_search(self):
        """Focus search entry"""
        # Find search entry widget and focus it
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Entry):
                        child.focus_set()
                        child.select_range(0, tk.END)
                        return
    
    def clear_search(self):
        """Clear search"""
        self.search_var.set("")
        self.filter_var.set("All")
        self.apply_filters()
    
    def refresh_current_folder(self):
        """Refresh current folder"""
        if self.current_folder:
            self.scan_folder()
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""{Settings.APP_NAME} v{Settings.APP_VERSION}

A specialized file explorer for .icd files with automated thumbnail generation.

Features:
• Direct file system access (no database)
• Instant search and filtering
• File metadata extraction
• Automated ICAD thumbnail generation
• Screen capture technology
• Thumbnail caching system
• Real-time preview
• Keyboard shortcuts

Supported file types:
{chr(10).join(f'• {ext}: {desc}' for ext, desc in Settings.ICAD_EXTENSIONS.items())}

Built for engineering productivity with ICAD integration!
"""
        messagebox.showinfo("About", about_text)
    
    def on_closing(self):
        """Handle application closing"""
        # Clean up any running processes
        if self.thumbnail_worker and self.thumbnail_worker.is_alive():
            print("Waiting for thumbnail generation to complete...")
        
        self.root.destroy()
    
    def run(self):
        """Run the application"""
        self.root.mainloop()

def main():
    """Main entry point"""
    print(f"Starting {Settings.APP_NAME} v{Settings.APP_VERSION}")
    print("With ICAD Screen Capture Integration")
    
    try:
        app = ICADFileExplorer()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        messagebox.showerror("Error", f"Failed to start application: {e}")

if __name__ == "__main__":
    main()