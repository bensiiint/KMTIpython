"""
File List Widget
Displays search results and handles file selection with keyboard navigation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Callable, Optional
from pathlib import Path
from datetime import datetime
import os

from core.database import DatabaseManager
from config.settings import Settings
from utils.file_utils import FileUtils

class FileListWidget:
    """File list widget with search results and keyboard navigation"""
    
    def __init__(self, parent: tk.Widget, db_manager: DatabaseManager, callback: Callable):
        self.parent = parent
        self.db_manager = db_manager
        self.callback = callback
        
        # Data
        self.files = []
        self.filtered_files = []
        self.selected_file = None
        self.sort_column = 'filename'
        self.sort_reverse = False
        
        # Setup UI
        self.setup_ui()
        self.setup_bindings()
        
        # Load initial data
        self.refresh()
    
    def setup_ui(self):
        """Setup file list UI"""
        # Main frame
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Toolbar
        self.setup_toolbar()
        
        # Treeview with scrollbars
        self.setup_treeview()
        
        # Context menu
        self.setup_context_menu()
    
    def setup_toolbar(self):
        """Setup file list toolbar"""
        self.toolbar = ttk.Frame(self.main_frame)
        self.toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # View mode buttons
        ttk.Label(self.toolbar, text="View:").pack(side=tk.LEFT)
        
        self.view_mode = tk.StringVar(value="details")
        
        ttk.Radiobutton(self.toolbar, text="Details", variable=self.view_mode, 
                       value="details", command=self.change_view_mode).pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Radiobutton(self.toolbar, text="List", variable=self.view_mode, 
                       value="list", command=self.change_view_mode).pack(side=tk.LEFT, padx=(5, 0))
        
        # Separator
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Sort options
        ttk.Label(self.toolbar, text="Sort:").pack(side=tk.LEFT)
        
        self.sort_var = tk.StringVar(value="filename")
        sort_combo = ttk.Combobox(self.toolbar, textvariable=self.sort_var,
                                 values=["filename", "project", "job", "company", "modified", "size"],
                                 state="readonly", width=10)
        sort_combo.pack(side=tk.LEFT, padx=(5, 0))
        sort_combo.bind('<<ComboboxSelected>>', self.on_sort_change)
        
        # Reverse sort
        self.reverse_var = tk.BooleanVar()
        ttk.Checkbutton(self.toolbar, text="Reverse", variable=self.reverse_var,
                       command=self.on_sort_change).pack(side=tk.LEFT, padx=(5, 0))
        
        # Separator
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Selection info
        self.selection_label = ttk.Label(self.toolbar, text="No selection")
        self.selection_label.pack(side=tk.RIGHT)
        
        # File count
        self.count_label = ttk.Label(self.toolbar, text="0 files")
        self.count_label.pack(side=tk.RIGHT, padx=(0, 10))
    
    def setup_treeview(self):
        """Setup treeview for file listing"""
        # Frame for treeview and scrollbars
        tree_frame = ttk.Frame(self.main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Define columns
        self.columns = {
            'filename': {'text': 'Filename', 'width': 200, 'anchor': tk.W},
            'project': {'text': 'Project', 'width': 120, 'anchor': tk.W},
            'job': {'text': 'Job', 'width': 120, 'anchor': tk.W},
            'company': {'text': 'Company', 'width': 120, 'anchor': tk.W},
            'type': {'text': 'Type', 'width': 60, 'anchor': tk.CENTER},
            'size': {'text': 'Size', 'width': 80, 'anchor': tk.E},
            'modified': {'text': 'Modified', 'width': 140, 'anchor': tk.W}
        }
        
        # Create treeview
        self.tree = ttk.Treeview(tree_frame, columns=list(self.columns.keys()), show='headings', height=15)
        
        # Configure columns
        for col_id, col_info in self.columns.items():
            self.tree.heading(col_id, text=col_info['text'], command=lambda c=col_id: self.sort_by_column(c))
            self.tree.column(col_id, width=col_info['width'], anchor=col_info['anchor'])
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Configure treeview grid
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Alternative row colors
        self.tree.tag_configure('evenrow', background='#f0f0f0')
        self.tree.tag_configure('oddrow', background='white')
        self.tree.tag_configure('selected', background='#0078d4', foreground='white')
    
    def setup_context_menu(self):
        """Setup right-click context menu"""
        self.context_menu = tk.Menu(self.parent, tearoff=0)
        
        self.context_menu.add_command(label="Open File", command=self.open_file)
        self.context_menu.add_command(label="Open Location", command=self.open_location)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Path", command=self.copy_path)
        self.context_menu.add_command(label="Copy Filename", command=self.copy_filename)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Properties", command=self.show_properties)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Remove from Database", command=self.remove_from_database)
    
    def setup_bindings(self):
        """Setup event bindings"""
        # Tree events
        self.tree.bind('<<TreeviewSelect>>', self.on_selection_change)
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<Return>', self.on_enter_key)
        self.tree.bind('<Button-3>', self.show_context_menu)  # Right click
        
        # Keyboard navigation
        self.tree.bind('<Up>', self.on_up_key)
        self.tree.bind('<Down>', self.on_down_key)
        self.tree.bind('<Home>', self.on_home_key)
        self.tree.bind('<End>', self.on_end_key)
        self.tree.bind('<Prior>', self.on_page_up)  # Page Up
        self.tree.bind('<Next>', self.on_page_down)  # Page Down
        
        # Selection keys
        self.tree.bind('<Control-a>', self.select_all)
        self.tree.bind('<Delete>', self.delete_selected)
        
        # Focus events
        self.tree.bind('<FocusIn>', self.on_focus_in)
        self.tree.bind('<FocusOut>', self.on_focus_out)
    
    def refresh(self):
        """Refresh file list from database"""
        try:
            self.files = self.db_manager.get_all_files()
            self.filtered_files = self.files.copy()
            self.update_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh file list: {e}")
    
    def update_results(self, files: List[Dict[str, Any]]):
        """Update file list with new results"""
        self.files = files
        self.filtered_files = files.copy()
        self.update_display()
    
    def update_display(self):
        """Update the treeview display"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Sort files
        self.sort_files()
        
        # Add files to tree
        for i, file_info in enumerate(self.filtered_files):
            self.add_file_to_tree(file_info, i)
        
        # Update counts
        self.update_counts()
        
        # Select first item if available
        if self.filtered_files:
            first_item = self.tree.get_children()[0]
            self.tree.selection_set(first_item)
            self.tree.focus(first_item)
    
    def add_file_to_tree(self, file_info: Dict[str, Any], index: int):
        """Add a file to the treeview"""
        # Prepare values
        values = []
        for col_id in self.columns.keys():
            if col_id == 'filename':
                values.append(file_info.get('filename', ''))
            elif col_id == 'project':
                values.append(file_info.get('project_name', ''))
            elif col_id == 'job':
                values.append(file_info.get('job_name', ''))
            elif col_id == 'company':
                values.append(file_info.get('company_name', ''))
            elif col_id == 'type':
                values.append(file_info.get('file_type', ''))
            elif col_id == 'size':
                size = file_info.get('file_size', 0)
                values.append(FileUtils.format_file_size(size))
            elif col_id == 'modified':
                modified = file_info.get('modified_time', '')
                if isinstance(modified, str):
                    try:
                        dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                        values.append(dt.strftime('%Y-%m-%d %H:%M'))
                    except:
                        values.append(modified)
                elif isinstance(modified, datetime):
                    values.append(modified.strftime('%Y-%m-%d %H:%M'))
                else:
                    values.append('')
        
        # Determine row tag for alternating colors
        tag = 'evenrow' if index % 2 == 0 else 'oddrow'
        
        # Add to tree
        item_id = self.tree.insert('', 'end', values=values, tags=(tag,))
        
        # Store file info with item
        self.tree.set(item_id, 'file_info', file_info)
    
    def sort_files(self):
        """Sort files based on current sort settings"""
        sort_column = self.sort_var.get()
        reverse = self.reverse_var.get()
        
        def sort_key(file_info):
            if sort_column == 'filename':
                return file_info.get('filename', '').lower()
            elif sort_column == 'project':
                return file_info.get('project_name', '').lower()
            elif sort_column == 'job':
                return file_info.get('job_name', '').lower()
            elif sort_column == 'company':
                return file_info.get('company_name', '').lower()
            elif sort_column == 'modified':
                modified = file_info.get('modified_time', '')
                if isinstance(modified, str):
                    try:
                        return datetime.fromisoformat(modified.replace('Z', '+00:00'))
                    except:
                        return datetime.min
                elif isinstance(modified, datetime):
                    return modified
                else:
                    return datetime.min
            elif sort_column == 'size':
                return file_info.get('file_size', 0)
            else:
                return ''
        
        self.filtered_files.sort(key=sort_key, reverse=reverse)
    
    def sort_by_column(self, column: str):
        """Sort by column header click"""
        if self.sort_var.get() == column:
            # Toggle reverse if same column
            self.reverse_var.set(not self.reverse_var.get())
        else:
            # New column, default to forward
            self.sort_var.set(column)
            self.reverse_var.set(False)
        
        self.update_display()
    
    def on_sort_change(self, event=None):
        """Handle sort option change"""
        self.update_display()
    
    def change_view_mode(self):
        """Change view mode between details and list"""
        mode = self.view_mode.get()
        
        if mode == "list":
            # Show only filename column
            for col in self.columns.keys():
                if col != 'filename':
                    self.tree.column(col, width=0)
                else:
                    self.tree.column(col, width=400)
        else:
            # Show all columns
            for col_id, col_info in self.columns.items():
                self.tree.column(col_id, width=col_info['width'])
    
    def update_counts(self):
        """Update file counts"""
        total_files = len(self.filtered_files)
        self.count_label.config(text=f"{total_files} file{'s' if total_files != 1 else ''}")
    
    def on_selection_change(self, event=None):
        """Handle selection change"""
        selected_items = self.tree.selection()
        
        if selected_items:
            item = selected_items[0]
            file_info = self.get_file_info_from_item(item)
            
            if file_info:
                self.selected_file = file_info
                self.callback(file_info)
                
                # Update selection label
                filename = file_info.get('filename', 'Unknown')
                self.selection_label.config(text=f"Selected: {filename}")
            else:
                self.selected_file = None
                self.callback(None)
                self.selection_label.config(text="No selection")
        else:
            self.selected_file = None
            self.callback(None)
            self.selection_label.config(text="No selection")
    
    def get_file_info_from_item(self, item) -> Optional[Dict[str, Any]]:
        """Get file info from tree item"""
        try:
            # Find file info by matching filename
            values = self.tree.item(item, 'values')
            if values:
                filename = values[0]
                for file_info in self.filtered_files:
                    if file_info.get('filename') == filename:
                        return file_info
        except:
            pass
        return None
    
    def on_double_click(self, event):
        """Handle double-click on file"""
        self.open_file()
    
    def on_enter_key(self, event):
        """Handle Enter key"""
        self.open_file()
    
    def on_up_key(self, event):
        """Handle Up arrow key"""
        self.navigate_selection(-1)
    
    def on_down_key(self, event):
        """Handle Down arrow key"""
        self.navigate_selection(1)
    
    def on_home_key(self, event):
        """Handle Home key"""
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])
            self.tree.see(children[0])
    
    def on_end_key(self, event):
        """Handle End key"""
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[-1])
            self.tree.focus(children[-1])
            self.tree.see(children[-1])
    
    def on_page_up(self, event):
        """Handle Page Up key"""
        self.navigate_selection(-10)
    
    def on_page_down(self, event):
        """Handle Page Down key"""
        self.navigate_selection(10)
    
    def navigate_selection(self, delta: int):
        """Navigate selection by delta"""
        children = self.tree.get_children()
        if not children:
            return
        
        current_selection = self.tree.selection()
        if not current_selection:
            # No selection, select first item
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])
            return
        
        # Find current index
        current_item = current_selection[0]
        try:
            current_index = children.index(current_item)
        except ValueError:
            return
        
        # Calculate new index
        new_index = current_index + delta
        new_index = max(0, min(len(children) - 1, new_index))
        
        # Select new item
        new_item = children[new_index]
        self.tree.selection_set(new_item)
        self.tree.focus(new_item)
        self.tree.see(new_item)
    
    def on_focus_in(self, event):
        """Handle focus in"""
        # Highlight selection
        selected_items = self.tree.selection()
        if selected_items:
            for item in selected_items:
                self.tree.item(item, tags=('selected',))
    
    def on_focus_out(self, event):
        """Handle focus out"""
        # Remove selection highlight
        selected_items = self.tree.selection()
        if selected_items:
            for item in selected_items:
                index = self.tree.index(item)
                tag = 'evenrow' if index % 2 == 0 else 'oddrow'
                self.tree.item(item, tags=(tag,))
    
    def show_context_menu(self, event):
        """Show context menu"""
        # Select item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.tree.focus(item)
            
            # Show context menu
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
    
    def open_file(self):
        """Open selected file"""
        if self.selected_file:
            file_path = self.selected_file.get('file_path', '')
            if file_path and Path(file_path).exists():
                try:
                    os.startfile(file_path)  # Windows
                except AttributeError:
                    os.system(f'xdg-open "{file_path}"')  # Linux
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to open file: {e}")
            else:
                messagebox.showwarning("File Not Found", "Selected file no longer exists.")
    
    def open_location(self):
        """Open file location in explorer"""
        if self.selected_file:
            file_path = self.selected_file.get('file_path', '')
            if file_path and Path(file_path).exists():
                try:
                    # Windows
                    os.startfile(Path(file_path).parent)
                except AttributeError:
                    # Linux
                    os.system(f'xdg-open "{Path(file_path).parent}"')
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to open location: {e}")
            else:
                messagebox.showwarning("File Not Found", "Selected file no longer exists.")
    
    def copy_path(self):
        """Copy file path to clipboard"""
        if self.selected_file:
            file_path = self.selected_file.get('file_path', '')
            if file_path:
                self.parent.clipboard_clear()
                self.parent.clipboard_append(file_path)
                messagebox.showinfo("Copied", "File path copied to clipboard.")
    
    def copy_filename(self):
        """Copy filename to clipboard"""
        if self.selected_file:
            filename = self.selected_file.get('filename', '')
            if filename:
                self.parent.clipboard_clear()
                self.parent.clipboard_append(filename)
                messagebox.showinfo("Copied", "Filename copied to clipboard.")
    
    def show_properties(self):
        """Show file properties dialog"""
        if self.selected_file:
            self.show_file_properties_dialog(self.selected_file)
    
    def show_file_properties_dialog(self, file_info: Dict[str, Any]):
        """Show file properties in a dialog"""
        # Create properties dialog
        dialog = tk.Toplevel(self.parent)
        dialog.title("File Properties")
        dialog.geometry("500x600")
        dialog.resizable(False, False)
        
        # Center dialog
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Create notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # General tab
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")
        
        # File info
        info_frame = ttk.LabelFrame(general_frame, text="File Information", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Add file info fields
        fields = [
            ("Filename:", file_info.get('filename', '')),
            ("Path:", file_info.get('file_path', '')),
            ("Size:", FileUtils.format_file_size(file_info.get('file_size', 0))),
            ("Type:", file_info.get('file_type', '')),
            ("Modified:", str(file_info.get('modified_time', ''))),
            ("Created:", str(file_info.get('created_time', ''))),
        ]
        
        for i, (label, value) in enumerate(fields):
            ttk.Label(info_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=2)
            ttk.Label(info_frame, text=str(value), wraplength=300).grid(row=i, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Project info
        project_frame = ttk.LabelFrame(general_frame, text="Project Information", padding=10)
        project_frame.pack(fill=tk.X, pady=(0, 10))
        
        project_fields = [
            ("Project:", file_info.get('project_name', '')),
            ("Job:", file_info.get('job_name', '')),
            ("Company:", file_info.get('company_name', '')),
        ]
        
        for i, (label, value) in enumerate(project_fields):
            ttk.Label(project_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=2)
            ttk.Label(project_frame, text=str(value), wraplength=300).grid(row=i, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Metadata tab
        metadata_frame = ttk.Frame(notebook)
        notebook.add(metadata_frame, text="Metadata")
        
        # Metadata text
        metadata_text = tk.Text(metadata_frame, wrap=tk.WORD, height=20)
        metadata_scrollbar = ttk.Scrollbar(metadata_frame, orient=tk.VERTICAL, command=metadata_text.yview)
        metadata_text.configure(yscrollcommand=metadata_scrollbar.set)
        
        metadata_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        metadata_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # Add metadata content
        metadata = file_info.get('metadata', {})
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                metadata_text.insert(tk.END, f"{key}: {value}\n")
        
        metadata_text.config(state=tk.DISABLED)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Open File", command=lambda: self.open_file()).pack(side=tk.RIGHT, padx=(0, 10))
    
    def remove_from_database(self):
        """Remove selected file from database"""
        if self.selected_file:
            result = messagebox.askyesno("Confirm Removal", 
                                       f"Remove '{self.selected_file.get('filename', '')}' from database?\n\n"
                                       "This will not delete the actual file.")
            if result:
                file_path = self.selected_file.get('file_path', '')
                if self.db_manager.remove_file(file_path):
                    self.refresh()
                    messagebox.showinfo("Removed", "File removed from database.")
                else:
                    messagebox.showerror("Error", "Failed to remove file from database.")
    
    def select_all(self, event=None):
        """Select all files"""
        children = self.tree.get_children()
        self.tree.selection_set(children)
    
    def delete_selected(self, event=None):
        """Handle delete key"""
        self.remove_from_database()
    
    def get_selected_files(self) -> List[Dict[str, Any]]:
        """Get all selected files"""
        selected_files = []
        selected_items = self.tree.selection()
        
        for item in selected_items:
            file_info = self.get_file_info_from_item(item)
            if file_info:
                selected_files.append(file_info)
        
        return selected_files
    
    def clear_selection(self):
        """Clear selection"""
        self.tree.selection_remove(self.tree.selection())
    
    def focus_list(self):
        """Focus on the file list"""
        self.tree.focus_set()
    
    def export_to_csv(self, filename: str) -> bool:
        """Export file list to CSV"""
        try:
            import csv
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                headers = ['Filename', 'Project', 'Job', 'Company', 'Type', 'Size', 'Modified', 'Path']
                writer.writerow(headers)
                
                # Write data
                for file_info in self.filtered_files:
                    row = [
                        file_info.get('filename', ''),
                        file_info.get('project_name', ''),
                        file_info.get('job_name', ''),
                        file_info.get('company_name', ''),
                        file_info.get('file_type', ''),
                        file_info.get('file_size', 0),
                        file_info.get('modified_time', ''),
                        file_info.get('file_path', '')
                    ]
                    writer.writerow(row)
            
            return True
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export file list: {e}")
            return False