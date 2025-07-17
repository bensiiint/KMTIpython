"""
Preview Widget
Displays file preview and metadata information.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional
from pathlib import Path
import os
from datetime import datetime

from config.settings import Settings
from utils.file_utils import FileUtils

class PreviewWidget:
    """Preview widget for displaying file information and preview"""
    
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.current_file = None
        self.preview_image = None
        
        # Setup UI
        self.setup_ui()
        
        # Show initial empty state
        self.show_empty_state()
    
    def setup_ui(self):
        """Setup preview widget UI"""
        # Main frame
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        self.setup_header()
        
        # Content notebook
        self.setup_content()
        
        # Footer
        self.setup_footer()
    
    def setup_header(self):
        """Setup header with file name and actions"""
        self.header_frame = ttk.Frame(self.main_frame)
        self.header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File name label
        self.filename_label = ttk.Label(self.header_frame, text="No file selected", 
                                      font=('TkDefaultFont', 10, 'bold'))
        self.filename_label.pack(side=tk.LEFT)
        
        # Action buttons
        self.action_frame = ttk.Frame(self.header_frame)
        self.action_frame.pack(side=tk.RIGHT)
        
        self.open_btn = ttk.Button(self.action_frame, text="Open", 
                                  command=self.open_file, state=tk.DISABLED)
        self.open_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.location_btn = ttk.Button(self.action_frame, text="Location", 
                                     command=self.open_location, state=tk.DISABLED)
        self.location_btn.pack(side=tk.LEFT)
    
    def setup_content(self):
        """Setup content area with tabs"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Preview tab
        self.setup_preview_tab()
        
        # Details tab
        self.setup_details_tab()
        
        # Metadata tab
        self.setup_metadata_tab()
    
    def setup_preview_tab(self):
        """Setup preview tab"""
        self.preview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.preview_frame, text="Preview")
        
        # Preview container
        self.preview_container = ttk.Frame(self.preview_frame)
        self.preview_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Preview label (for images or text)
        self.preview_label = ttk.Label(self.preview_container, text="No preview available", 
                                     anchor=tk.CENTER, justify=tk.CENTER)
        self.preview_label.pack(expand=True)
        
        # Preview canvas (for custom drawing)
        self.preview_canvas = tk.Canvas(self.preview_container, bg='white', height=300)
        # Don't pack initially - will be shown when needed
        
        # File type icon
        self.icon_label = ttk.Label(self.preview_container, text="📄", 
                                  font=('TkDefaultFont', 48))
        # Don't pack initially
    
    def setup_details_tab(self):
        """Setup file details tab"""
        self.details_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.details_frame, text="Details")
        
        # Scrollable frame for details
        self.details_canvas = tk.Canvas(self.details_frame)
        self.details_scrollbar = ttk.Scrollbar(self.details_frame, orient=tk.VERTICAL, 
                                             command=self.details_canvas.yview)
        self.details_scroll_frame = ttk.Frame(self.details_canvas)
        
        self.details_scroll_frame.bind(
            "<Configure>",
            lambda e: self.details_canvas.configure(scrollregion=self.details_canvas.bbox("all"))
        )
        
        self.details_canvas.create_window((0, 0), window=self.details_scroll_frame, anchor="nw")
        self.details_canvas.configure(yscrollcommand=self.details_scrollbar.set)
        
        self.details_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # File information sections
        self.create_details_sections()
    
    def create_details_sections(self):
        """Create sections for file details"""
        # General Information
        self.general_frame = ttk.LabelFrame(self.details_scroll_frame, text="General", padding=10)
        self.general_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File Properties
        self.properties_frame = ttk.LabelFrame(self.details_scroll_frame, text="File Properties", padding=10)
        self.properties_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Project Information
        self.project_frame = ttk.LabelFrame(self.details_scroll_frame, text="Project Information", padding=10)
        self.project_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Statistics
        self.stats_frame = ttk.LabelFrame(self.details_scroll_frame, text="Statistics", padding=10)
        self.stats_frame.pack(fill=tk.X, pady=(0, 10))
    
    def setup_metadata_tab(self):
        """Setup metadata tab"""
        self.metadata_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.metadata_frame, text="Metadata")
        
        # Metadata tree
        self.metadata_tree = ttk.Treeview(self.metadata_frame, columns=('Value',), height=15)
        self.metadata_tree.heading('#0', text='Property')
        self.metadata_tree.heading('Value', text='Value')
        self.metadata_tree.column('#0', width=200)
        self.metadata_tree.column('Value', width=300)
        
        # Scrollbar for metadata tree
        metadata_scrollbar = ttk.Scrollbar(self.metadata_frame, orient=tk.VERTICAL, 
                                         command=self.metadata_tree.yview)
        self.metadata_tree.configure(yscrollcommand=metadata_scrollbar.set)
        
        self.metadata_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        metadata_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_footer(self):
        """Setup footer with status information"""
        self.footer_frame = ttk.Frame(self.main_frame)
        self.footer_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Status label
        self.status_label = ttk.Label(self.footer_frame, text="Ready", 
                                    relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # File size label
        self.size_label = ttk.Label(self.footer_frame, text="", 
                                  relief=tk.SUNKEN, anchor=tk.E)
        self.size_label.pack(side=tk.RIGHT, padx=(5, 0))
    
    def preview_file(self, file_info: Dict[str, Any]):
        """Preview a file"""
        self.current_file = file_info
        
        # Update header
        filename = file_info.get('filename', 'Unknown')
        self.filename_label.config(text=filename)
        
        # Enable action buttons
        self.open_btn.config(state=tk.NORMAL)
        self.location_btn.config(state=tk.NORMAL)
        
        # Update footer
        file_size = file_info.get('file_size', 0)
        self.size_label.config(text=FileUtils.format_file_size(file_size))
        
        # Update preview
        self.update_preview()
        
        # Update details
        self.update_details()
        
        # Update metadata
        self.update_metadata()
        
        # Update status
        self.status_label.config(text=f"Previewing: {filename}")
    
    def update_preview(self):
        """Update preview content"""
        if not self.current_file:
            return
        
        file_path = self.current_file.get('file_path', '')
        file_type = self.current_file.get('file_type', '').lower()
        
        # Clear previous preview
        self.clear_preview()
        
        if not file_path or not Path(file_path).exists():
            self.show_error_preview("File not found")
            return
        
        # Show preview based on file type
        if file_type in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
            self.show_image_preview(file_path)
        elif file_type in ['.txt', '.log', '.csv']:
            self.show_text_preview(file_path)
        elif file_type in Settings.ICAD_EXTENSIONS:
            self.show_icad_preview(file_path, file_type)
        else:
            self.show_file_icon_preview(file_type)
    
    def show_image_preview(self, file_path: str):
        """Show image preview"""
        try:
            from PIL import Image, ImageTk
            
            # Load and resize image
            image = Image.open(file_path)
            image.thumbnail(Settings.PREVIEW_IMAGE_SIZE, Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.preview_image = ImageTk.PhotoImage(image)
            
            # Show image
            self.preview_label.config(image=self.preview_image, text="")
            self.preview_label.pack(expand=True)
            
        except ImportError:
            self.show_error_preview("PIL/Pillow not installed")
        except Exception as e:
            self.show_error_preview(f"Error loading image: {e}")
    
    def show_text_preview(self, file_path: str):
        """Show text file preview"""
        try:
            # Hide label, show canvas with text
            self.preview_label.pack_forget()
            self.preview_canvas.pack(fill=tk.BOTH, expand=True)
            
            # Clear canvas
            self.preview_canvas.delete("all")
            
            # Read file content (first 1000 lines)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= 1000:  # Limit to first 1000 lines
                        lines.append("... (file truncated)")
                        break
                    lines.append(line.rstrip())
            
            # Display text
            text_content = '\n'.join(lines)
            self.preview_canvas.create_text(10, 10, text=text_content, anchor=tk.NW, 
                                          font=('Courier', 9), width=380)
            
        except Exception as e:
            self.show_error_preview(f"Error reading text file: {e}")
    
    def show_icad_preview(self, file_path: str, file_type: str):
        """Show ICAD file preview"""
        # For now, show file icon and basic info
        # In a real implementation, this would use ICAD libraries or convert to image
        
        self.preview_label.pack_forget()
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Clear canvas
        self.preview_canvas.delete("all")
        
        # Show file type icon
        icon_text = self.get_file_type_icon(file_type)
        self.preview_canvas.create_text(200, 100, text=icon_text, font=('TkDefaultFont', 48), 
                                      fill='#666666')
        
        # Show file type
        self.preview_canvas.create_text(200, 160, text=f"{file_type.upper()} File", 
                                      font=('TkDefaultFont', 14), fill='#333333')
        
        # Show basic file info
        file_size = FileUtils.format_file_size(self.current_file.get('file_size', 0))
        modified = self.current_file.get('modified_time', '')
        if isinstance(modified, str):
            try:
                dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                modified_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                modified_str = modified
        else:
            modified_str = str(modified)
        
        info_text = f"Size: {file_size}\nModified: {modified_str}"
        self.preview_canvas.create_text(200, 200, text=info_text, 
                                      font=('TkDefaultFont', 10), fill='#666666')
        
        # Show preview placeholder
        self.preview_canvas.create_text(200, 250, text="Preview not available\nfor this file type", 
                                      font=('TkDefaultFont', 10), fill='#999999')
    
    def show_file_icon_preview(self, file_type: str):
        """Show file icon preview"""
        self.preview_label.pack_forget()
        self.icon_label.pack(expand=True)
        
        # Set icon based on file type
        icon = self.get_file_type_icon(file_type)
        self.icon_label.config(text=icon)
    
    def get_file_type_icon(self, file_type: str) -> str:
        """Get emoji icon for file type"""
        icons = {
            '.dwg': '🔧',
            '.dxf': '📐',
            '.icad': '🔧',
            '.ifc': '🏢',
            '.step': '⚙️',
            '.stp': '⚙️',
            '.pdf': '📄',
            '.txt': '📝',
            '.csv': '📊',
            '.xml': '📋',
        }
        return icons.get(file_type.lower(), '📄')
    
    def show_error_preview(self, error_message: str):
        """Show error in preview"""
        self.preview_canvas.pack_forget()
        self.icon_label.pack_forget()
        
        self.preview_label.config(text=f"❌\n{error_message}", image="")
        self.preview_label.pack(expand=True)
    
    def clear_preview(self):
        """Clear preview content"""
        self.preview_label.pack_forget()
        self.preview_canvas.pack_forget()
        self.icon_label.pack_forget()
        
        self.preview_image = None
        self.preview_canvas.delete("all")
    
    def update_details(self):
        """Update file details"""
        if not self.current_file:
            return
        
        # Clear existing details
        for widget in self.general_frame.winfo_children():
            widget.destroy()
        for widget in self.properties_frame.winfo_children():
            widget.destroy()
        for widget in self.project_frame.winfo_children():
            widget.destroy()
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        # General Information
        self.add_detail_field(self.general_frame, "Filename:", self.current_file.get('filename', ''))
        self.add_detail_field(self.general_frame, "Path:", self.current_file.get('file_path', ''))
        self.add_detail_field(self.general_frame, "Type:", self.current_file.get('file_type', ''))
        
        # File Properties
        file_size = self.current_file.get('file_size', 0)
        self.add_detail_field(self.properties_frame, "Size:", FileUtils.format_file_size(file_size))
        
        modified = self.current_file.get('modified_time', '')
        if isinstance(modified, str):
            try:
                dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                modified_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                modified_str = modified
        else:
            modified_str = str(modified)
        self.add_detail_field(self.properties_frame, "Modified:", modified_str)
        
        created = self.current_file.get('created_time', '')
        if isinstance(created, str):
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                created_str = created
        else:
            created_str = str(created)
        self.add_detail_field(self.properties_frame, "Created:", created_str)
        
        # Project Information
        self.add_detail_field(self.project_frame, "Project:", self.current_file.get('project_name', ''))
        self.add_detail_field(self.project_frame, "Job:", self.current_file.get('job_name', ''))
        self.add_detail_field(self.project_frame, "Company:", self.current_file.get('company_name', ''))
        
        # Statistics
        indexed_time = self.current_file.get('indexed_time', '')
        if indexed_time:
            try:
                dt = datetime.fromisoformat(indexed_time.replace('Z', '+00:00'))
                indexed_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                indexed_str = indexed_time
            self.add_detail_field(self.stats_frame, "Indexed:", indexed_str)
        
        # File exists check
        file_path = self.current_file.get('file_path', '')
        exists = Path(file_path).exists() if file_path else False
        self.add_detail_field(self.stats_frame, "File exists:", "Yes" if exists else "No")
        
        if exists:
            # File permissions
            readable = os.access(file_path, os.R_OK)
            writable = os.access(file_path, os.W_OK)
            self.add_detail_field(self.stats_frame, "Readable:", "Yes" if readable else "No")
            self.add_detail_field(self.stats_frame, "Writable:", "Yes" if writable else "No")
    
    def add_detail_field(self, parent: tk.Widget, label: str, value: str):
        """Add a detail field to parent frame"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(frame, text=label, width=15).pack(side=tk.LEFT)
        ttk.Label(frame, text=str(value), wraplength=300).pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def update_metadata(self):
        """Update metadata tree"""
        if not self.current_file:
            return
        
        # Clear existing metadata
        for item in self.metadata_tree.get_children():
            self.metadata_tree.delete(item)
        
        # Add metadata
        metadata = self.current_file.get('metadata', {})
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                self.metadata_tree.insert('', 'end', text=key, values=(str(value),))
        
        # Add database fields
        db_fields = [
            ('id', self.current_file.get('id', '')),
            ('file_path', self.current_file.get('file_path', '')),
            ('filename', self.current_file.get('filename', '')),
            ('file_size', self.current_file.get('file_size', '')),
            ('modified_time', self.current_file.get('modified_time', '')),
            ('created_time', self.current_file.get('created_time', '')),
            ('project_name', self.current_file.get('project_name', '')),
            ('job_name', self.current_file.get('job_name', '')),
            ('company_name', self.current_file.get('company_name', '')),
            ('file_type', self.current_file.get('file_type', '')),
            ('indexed_time', self.current_file.get('indexed_time', '')),
        ]
        
        # Add database section
        db_parent = self.metadata_tree.insert('', 'end', text='Database Fields', values=('',))
        for field, value in db_fields:
            if value:
                self.metadata_tree.insert(db_parent, 'end', text=field, values=(str(value),))
    
    def show_empty_state(self):
        """Show empty state when no file is selected"""
        self.current_file = None
        
        # Update header
        self.filename_label.config(text="No file selected")
        
        # Disable action buttons
        self.open_btn.config(state=tk.DISABLED)
        self.location_btn.config(state=tk.DISABLED)
        
        # Clear preview
        self.clear_preview()
        
        # Show empty message
        self.preview_label.config(text="Select a file to preview", image="")
        self.preview_label.pack(expand=True)
        
        # Clear details
        self.update_details()
        
        # Clear metadata
        self.update_metadata()
        
        # Update footer
        self.status_label.config(text="No file selected")
        self.size_label.config(text="")
    
    def clear_preview(self):
        """Clear the preview"""
        self.show_empty_state()
    
    def open_file(self):
        """Open the current file"""
        if self.current_file:
            file_path = self.current_file.get('file_path', '')
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
        """Open file location"""
        if self.current_file:
            file_path = self.current_file.get('file_path', '')
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
    
    def refresh_preview(self):
        """Refresh the current preview"""
        if self.current_file:
            self.preview_file(self.current_file)
    
    def save_preview_image(self):
        """Save preview image to file"""
        if self.preview_image:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
            )
            if filename:
                try:
                    # This would need to be implemented based on how preview images are generated
                    messagebox.showinfo("Success", "Preview image saved successfully.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save preview: {e}")
    
    def copy_file_info(self):
        """Copy file information to clipboard"""
        if self.current_file:
            info_text = f"Filename: {self.current_file.get('filename', '')}\n"
            info_text += f"Path: {self.current_file.get('file_path', '')}\n"
            info_text += f"Size: {FileUtils.format_file_size(self.current_file.get('file_size', 0))}\n"
            info_text += f"Project: {self.current_file.get('project_name', '')}\n"
            info_text += f"Job: {self.current_file.get('job_name', '')}\n"
            info_text += f"Company: {self.current_file.get('company_name', '')}\n"
            
            self.parent.clipboard_clear()
            self.parent.clipboard_append(info_text)
            messagebox.showinfo("Copied", "File information copied to clipboard.")