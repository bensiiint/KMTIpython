# Update your main_window.py - replace the preview widget setup section

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
    
    # UPDATED: Use simplified preview widget
    self.preview_widget = PreviewWidget(right_panel)
    
    # Configure initial pane sizes
    self.root.after(100, lambda: self.paned_window.sashpos(0, 800))