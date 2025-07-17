"""
Main Application Window
Handles the primary interface layout and coordination between components.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

from config.settings import Settings
from utils.config_utils import ConfigUtils
from core.database import DatabaseManager
from core.file_scanner import FileScanner
from core.search_engine import SearchEngine
from gui.search_widget import SearchWidget
from gui.file_list_widget import FileListWidget
from gui.preview_widget import PreviewWidget

class MainWindow:
    """Main application window"""
    
    def __init__(self, root: tk.Tk, db_manager: DatabaseManager, file_scanner: FileScanner):
        self.root = root
        self.db_manager = db_manager
        self.file_scanner = file_scanner
        self.search_engine = SearchEngine(db_manager)
        self.config = ConfigUtils()
        
        # Initialize variables
        self.current_scan_thread = None
        self.scan_progress_var = tk.DoubleVar()
        self.scan_status_var = tk.StringVar(value="Ready")
        self.selected_file = None
        
        # Setup UI
        self.setup_window()
        self.setup_menu()
        self.setup_toolbar()
        self.setup_main_layout()
        self.setup_status_bar()
        self.setup_bindings()
        
        # Load window geometry
        self.load_window_geometry()
        
        # Initialize components
        self.file_list_widget.refresh()
        
        # Setup scan completion callback
        self.file_scanner.progress_callback = self.on_scan_progress
    
    def setup_window(self):
        """Setup main window properties"""
        self.root.title(f"{Settings.APP_NAME} v{Settings.APP_VERSION}")
        self.root.minsize(Settings.MIN_WINDOW_WIDTH, Settings.MIN_WINDOW_HEIGHT)
        
        # Center window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - Settings.WINDOW_WIDTH) // 2
        y = (screen_height - Settings.WINDOW_HEIGHT) // 2
        self.root.geometry(f"{Settings.WINDOW_WIDTH}x{Settings.WINDOW_HEIGHT}+{x}+{y}")
        
        # Configure window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_menu(self):
        """Setup application menu bar"""
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # File menu
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Scan Directory...", command=self.scan_directory, accelerator="Ctrl+O")
        file_menu.add_command(label="Rescan Current", command=self.rescan_current, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Add to Favorites", command=self.add_to_favorites)
        file_menu.add_command(label="Manage Favorites", command=self.manage_favorites)
        file_menu.add_separator()
        file_menu.add_command(label="Export File List...", command=self.export_file_list)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Ctrl+Q")
        
        # Edit menu
        edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Find...", command=self.focus_search, accelerator="Ctrl+F")
        edit_menu.add_command(label="Clear Search", command=self.clear_search, accelerator="Ctrl+L")
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All", command=self.select_all, accelerator="Ctrl+A")
        edit_menu.add_command(label="Copy Path", command=self.copy_path, accelerator="Ctrl+C")
        edit_menu.add_separator()
        edit_menu.add_command(label="Preferences...", command=self.show_preferences)
        
        # View menu
        view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self.refresh_view, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Show Toolbar", command=self.toggle_toolbar)
        view_menu.add_checkbutton(label="Show Status Bar", command=self.toggle_statusbar)
        view_menu.add_separator()
        view_menu.add_command(label="Statistics...", command=self.show_statistics)
        
        # Tools menu
        tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Database Cleanup", command=self.cleanup_database)
        tools_menu.add_command(label="Find Duplicates", command=self.find_duplicates)
        tools_menu.add_command(label="Backup Database", command=self.backup_database)
        tools_menu.add_separator()
        tools_menu.add_command(label="Watch Directories", command=self.manage_watched_directories)
        
        # Help menu
        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self.show_user_guide)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
    
    def setup_toolbar(self):
        """Setup toolbar with common actions"""
        self.toolbar = ttk.Frame(self.root)
        self.toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        # Scan button
        self.scan_btn = ttk.Button(self.toolbar, text="Scan Directory", command=self.scan_directory)
        self.scan_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Refresh button
        self.refresh_btn = ttk.Button(self.toolbar, text="Refresh", command=self.refresh_view)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Separator
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Quick actions
        ttk.Label(self.toolbar, text="Quick:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Favorites dropdown
        self.favorites_var = tk.StringVar()
        self.favorites_combo = ttk.Combobox(self.toolbar, textvariable=self.favorites_var, 
                                          state="readonly", width=20)
        self.favorites_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.favorites_combo.bind('<<ComboboxSelected>>', self.on_favorite_selected)
        
        # Update favorites
        self.update_favorites_combo()
        
        # Separator
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # File count label
        self.file_count_label = ttk.Label(self.toolbar, text="0 files")
        self.file_count_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Progress bar (hidden by default)
        self.progress_bar = ttk.Progressbar(self.toolbar, mode='determinate', 
                                          variable=self.scan_progress_var)
        # Don't pack initially - will be shown during scanning
    
    def setup_main_layout(self):
        """Setup main content layout"""
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create paned window for resizable panels
        self.paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel (search + file list)
        left_panel = ttk.Frame(self.paned_window)
        self.paned_window.add(left_panel, weight=2)
        
        # Search widget
        self.search_widget = SearchWidget(left_panel, self.search_engine, self.on_search_results)
        
        # File list widget
        self.file_list_widget = FileListWidget(left_panel, self.db_manager, self.on_file_selected)
        
        # Right panel (preview)
        right_panel = ttk.Frame(self.paned_window)
        self.paned_window.add(right_panel, weight=1)
        
        # Preview widget
        self.preview_widget = PreviewWidget(right_panel)
        
        # Configure initial pane sizes
        self.root.after(100, lambda: self.paned_window.sashpos(0, 800))
    
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
        
        # Status label
        self.status_label = ttk.Label(self.status_frame, textvariable=self.scan_status_var)
        self.status_label.pack(side=tk.LEFT)
        
        # Separator
        ttk.Separator(self.status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Database info
        self.db_info_label = ttk.Label(self.status_frame, text="")
        self.db_info_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Update database info
        self.update_database_info()
    
    def setup_bindings(self):
        """Setup keyboard bindings"""
        # Global bindings
        self.root.bind('<Control-o>', lambda e: self.scan_directory())
        self.root.bind('<Control-f>', lambda e: self.focus_search())
        self.root.bind('<Control-l>', lambda e: self.clear_search())
        self.root.bind('<Control-a>', lambda e: self.select_all())
        self.root.bind('<Control-c>', lambda e: self.copy_path())
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        self.root.bind('<F5>', lambda e: self.refresh_view())
        self.root.bind('<Escape>', lambda e: self.clear_search())
        
        # Window state events
        self.root.bind('<Configure>', self.on_window_configure)
    
    def load_window_geometry(self):
        """Load window geometry from config"""
        geometry = self.config.get_window_geometry()
        
        if geometry['maximized']:
            self.root.state('zoomed')
        else:
            width = geometry['width']
            height = geometry['height']
            x = geometry['x'] or (self.root.winfo_screenwidth() - width) // 2
            y = geometry['y'] or (self.root.winfo_screenheight() - height) // 2
            self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def save_window_geometry(self):
        """Save current window geometry"""
        if self.root.state() == 'zoomed':
            self.config.save_window_geometry(0, 0, 0, 0, True)
        else:
            geometry = self.root.geometry()
            # Parse geometry string "WIDTHxHEIGHT+X+Y"
            parts = geometry.split('+')
            size_parts = parts[0].split('x')
            width = int(size_parts[0])
            height = int(size_parts[1])
            x = int(parts[1]) if len(parts) > 1 else 0
            y = int(parts[2]) if len(parts) > 2 else 0
            self.config.save_window_geometry(width, height, x, y, False)
    
    def on_window_configure(self, event):
        """Handle window resize/move events"""
        if event.widget == self.root:
            # Save geometry after a delay to avoid too many saves
            self.root.after_cancel(getattr(self, '_save_geometry_after', None))
            self._save_geometry_after = self.root.after(1000, self.save_window_geometry)
    
    def on_search_results(self, results: List[Dict[str, Any]]):
        """Handle search results"""
        self.file_list_widget.update_results(results)
        count = len(results)
        self.file_count_label.config(text=f"{count} file{'s' if count != 1 else ''}")
        
        if count == 0:
            self.scan_status_var.set("No files found")
        else:
            self.scan_status_var.set(f"Found {count} files")
    
    def on_file_selected(self, file_info: Optional[Dict[str, Any]]):
        """Handle file selection"""
        self.selected_file = file_info
        
        if file_info:
            self.preview_widget.preview_file(file_info)
            filename = file_info.get('filename', 'Unknown')
            self.scan_status_var.set(f"Selected: {filename}")
        else:
            self.preview_widget.clear_preview()
            self.scan_status_var.set("No file selected")
    
    def on_scan_progress(self, progress: float, current_file: str):
        """Handle scan progress updates"""
        self.scan_progress_var.set(progress)
        filename = Path(current_file).name
        self.scan_status_var.set(f"Scanning: {filename}")
        self.root.update_idletasks()
    
    def scan_directory(self):
        """Scan directory for ICAD files"""
        if self.current_scan_thread and self.current_scan_thread.is_alive():
            messagebox.showwarning("Scan in Progress", "A scan is already in progress.")
            return
        
        # Get directory from user
        last_dir = self.config.get_last_scan_directory()
        directory = filedialog.askdirectory(
            title="Select Directory to Scan",
            initialdir=last_dir if last_dir else None
        )
        
        if directory:
            self.start_directory_scan(directory)
    
    def start_directory_scan(self, directory: str):
        """Start directory scan in background thread"""
        self.config.set_last_scan_directory(directory)
        
        # Show progress bar
        self.progress_bar.pack(side=tk.LEFT, padx=(10, 0))
        self.scan_progress_var.set(0)
        self.scan_status_var.set("Starting scan...")
        
        # Disable scan button
        self.scan_btn.config(state='disabled', text='Scanning...')
        
        def scan_thread():
            try:
                result = self.file_scanner.scan_directory(directory)
                self.root.after(0, lambda: self.scan_completed(result))
            except Exception as e:
                self.root.after(0, lambda: self.scan_error(str(e)))
        
        self.current_scan_thread = threading.Thread(target=scan_thread, daemon=True)
        self.current_scan_thread.start()
    
    def scan_completed(self, result: Dict[str, Any]):
        """Handle scan completion"""
        # Hide progress bar
        self.progress_bar.pack_forget()
        
        # Enable scan button
        self.scan_btn.config(state='normal', text='Scan Directory')
        
        # Update status
        files_found = result['files_found']
        files_indexed = result['files_indexed']
        duration = result['scan_duration']
        
        self.scan_status_var.set(f"Scan complete: {files_indexed}/{files_found} files indexed in {duration:.1f}s")
        
        # Refresh file list
        self.file_list_widget.refresh()
        self.update_database_info()
        
        # Show completion message
        if self.config.get('notifications.show_scan_complete', True):
            messagebox.showinfo("Scan Complete", 
                              f"Scan completed successfully!\\n\\n"
                              f"Files found: {files_found}\\n"
                              f"Files indexed: {files_indexed}\\n"
                              f"Duration: {duration:.1f} seconds")
    
    def scan_error(self, error_msg: str):
        """Handle scan error"""
        # Hide progress bar
        self.progress_bar.pack_forget()
        
        # Enable scan button
        self.scan_btn.config(state='normal', text='Scan Directory')
        
        # Update status
        self.scan_status_var.set("Scan failed")
        
        # Show error message
        messagebox.showerror("Scan Error", f"Error scanning directory:\\n{error_msg}")
    
    def stop_scan(self):
        """Stop current scan"""
        if self.current_scan_thread and self.current_scan_thread.is_alive():
            self.file_scanner.stop_scanning()
            self.scan_status_var.set("Stopping scan...")
    
    def rescan_current(self):
        """Rescan the last scanned directory"""
        last_dir = self.config.get_last_scan_directory()
        if last_dir and Path(last_dir).exists():
            self.start_directory_scan(last_dir)
        else:
            messagebox.showwarning("No Directory", "No previous scan directory found.")
    
    def refresh_view(self):
        """Refresh the current view"""
        self.file_list_widget.refresh()
        self.update_database_info()
        self.scan_status_var.set("View refreshed")
    
    def focus_search(self):
        """Focus on search entry"""
        self.search_widget.focus_search()
    
    def clear_search(self):
        """Clear search and show all files"""
        self.search_widget.clear_search()
    
    def select_all(self):
        """Select all files in the list"""
        self.file_list_widget.select_all()
    
    def copy_path(self):
        """Copy selected file path to clipboard"""
        if self.selected_file:
            file_path = self.selected_file.get('file_path', '')
            if file_path:
                self.root.clipboard_clear()
                self.root.clipboard_append(file_path)
                self.scan_status_var.set("Path copied to clipboard")
    
    def add_to_favorites(self):
        """Add current directory to favorites"""
        last_dir = self.config.get_last_scan_directory()
        if last_dir:
            self.config.add_favorite_directory(last_dir)
            self.update_favorites_combo()
            self.scan_status_var.set("Added to favorites")
    
    def manage_favorites(self):
        """Open favorites management dialog"""
        # TODO: Implement favorites management dialog
        messagebox.showinfo("Not Implemented", "Favorites management dialog not yet implemented.")
    
    def export_file_list(self):
        """Export file list to CSV"""
        # TODO: Implement file list export
        messagebox.showinfo("Not Implemented", "File list export not yet implemented.")
    
    def show_preferences(self):
        """Show preferences dialog"""
        # TODO: Implement preferences dialog
        messagebox.showinfo("Not Implemented", "Preferences dialog not yet implemented.")
    
    def show_statistics(self):
        """Show database statistics"""
        stats = self.db_manager.get_statistics()
        
        message = f"Database Statistics:\\n\\n"
        message += f"Total Files: {stats.get('total_files', 0):,}\\n"
        message += f"Recent Files (7 days): {stats.get('recent_files', 0):,}\\n"
        message += f"Total Size: {self._format_size(stats.get('total_size', 0))}\\n\\n"
        
        files_by_type = stats.get('files_by_type', {})
        if files_by_type:
            message += "Files by Type:\\n"
            for file_type, count in files_by_type.items():
                message += f"  {file_type}: {count:,}\\n"
        
        messagebox.showinfo("Database Statistics", message)
    
    def cleanup_database(self):
        """Clean up database entries for missing files"""
        result = messagebox.askyesno("Database Cleanup", 
                                   "This will remove database entries for files that no longer exist. Continue?")
        if result:
            removed = self.db_manager.cleanup_missing_files()
            self.file_list_widget.refresh()
            self.update_database_info()
            messagebox.showinfo("Cleanup Complete", f"Removed {removed} missing file entries.")
    
    def find_duplicates(self):
        """Find duplicate files"""
        # TODO: Implement duplicate finder
        messagebox.showinfo("Not Implemented", "Duplicate finder not yet implemented.")
    
    def backup_database(self):
        """Create database backup"""
        # TODO: Implement database backup
        messagebox.showinfo("Not Implemented", "Database backup not yet implemented.")
    
    def manage_watched_directories(self):
        """Manage watched directories"""
        # TODO: Implement watched directories management
        messagebox.showinfo("Not Implemented", "Watched directories management not yet implemented.")
    
    def toggle_toolbar(self):
        """Toggle toolbar visibility"""
        # TODO: Implement toolbar toggle
        pass
    
    def toggle_statusbar(self):
        """Toggle status bar visibility"""
        # TODO: Implement status bar toggle
        pass
    
    def show_user_guide(self):
        """Show user guide"""
        messagebox.showinfo("User Guide", "User guide not yet available.")
    
    def show_shortcuts(self):
        """Show keyboard shortcuts"""
        shortcuts = """Keyboard Shortcuts:

File Operations:
Ctrl+O - Scan Directory
F5 - Refresh View
Ctrl+Q - Exit

Search:
Ctrl+F - Focus Search
Ctrl+L - Clear Search
Escape - Clear Search

Selection:
Ctrl+A - Select All
Ctrl+C - Copy Path

Navigation:
Arrow Keys - Navigate File List
Enter - Open File
Space - Toggle Selection"""
        
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""{Settings.APP_NAME} v{Settings.APP_VERSION}

A desktop application for managing and previewing ICAD files.

Designed to help engineers quickly search and preview ICAD files, 
reducing search time from hours to minutes.

Features:
• Fast search by filename, project, job, or company
• Instant file preview
• Keyboard navigation
• File indexing and metadata extraction

© 2024 Engineering Team"""
        
        messagebox.showinfo("About", about_text)
    
    def update_favorites_combo(self):
        """Update favorites combobox"""
        favorites = self.config.get_favorite_directories()
        self.favorites_combo['values'] = favorites
        
        if favorites:
            self.favorites_combo.set(favorites[0] if favorites else "")
    
    def on_favorite_selected(self, event):
        """Handle favorite directory selection"""
        selected = self.favorites_var.get()
        if selected and Path(selected).exists():
            self.start_directory_scan(selected)
    
    def update_database_info(self):
        """Update database info in status bar"""
        file_count = self.db_manager.get_file_count()
        self.db_info_label.config(text=f"Database: {file_count:,} files")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def on_closing(self):
        """Handle application closing"""
        # Stop any running scan
        if self.current_scan_thread and self.current_scan_thread.is_alive():
            self.file_scanner.stop_scanning()
        
        # Save window geometry
        self.save_window_geometry()
        
        # Close application
        self.root.destroy()