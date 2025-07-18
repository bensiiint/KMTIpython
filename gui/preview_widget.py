"""
Simplified Preview Widget with Working ICAD Screen Capture
Replaces complex 3D libraries with your working screen capture system.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional
from pathlib import Path
import os
from datetime import datetime
import threading

# Import your working screen capture system
from icad_screen_capture import ICADScreenCapture

class ThumbnailWorker(threading.Thread):
    """Background worker for generating thumbnails"""
    
    def __init__(self, file_path: str, screen_capture: ICADScreenCapture, callback):
        super().__init__(daemon=True)
        self.file_path = file_path
        self.screen_capture = screen_capture
        self.callback = callback
        
    def run(self):
        try:
            # Generate thumbnail using your working screen capture
            thumbnail_path = self.screen_capture.generate_thumbnail(Path(self.file_path))
            
            if thumbnail_path:
                self.callback(str(thumbnail_path), None)
            else:
                self.callback(None, "Could not generate thumbnail")
                
        except Exception as e:
            self.callback(None, f"Error: {e}")

class PreviewWidget:
    """Simplified preview widget with working ICAD screen capture"""
    
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.current_file = None
        self.preview_image = None
        self.screen_capture = ICADScreenCapture()
        self.thumbnail_worker = None
        
        # Setup UI
        self.setup_ui()
        
        # Show initial empty state
        self.show_empty_state()
    
    def setup_ui(self):
        """Setup preview widget UI"""
        # Main frame
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with file actions
        self.setup_header()
        
        # Content notebook with tabs
        self.setup_content()
        
        # Footer with status
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
        self.location_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.refresh_btn = ttk.Button(self.action_frame, text="🔄 Refresh", 
                                    command=self.refresh_thumbnail, state=tk.DISABLED)
        self.refresh_btn.pack(side=tk.LEFT)
    
    def setup_content(self):
        """Setup content area with tabs"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Thumbnail tab
        self.setup_thumbnail_tab()
        
        # Details tab
        self.setup_details_tab()
    
    def setup_thumbnail_tab(self):
        """Setup thumbnail preview tab"""
        self.thumbnail_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.thumbnail_frame, text="Thumbnail")
        
        # Thumbnail display area
        self.thumbnail_container = ttk.Frame(self.thumbnail_frame)
        self.thumbnail_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas for thumbnail display
        self.thumbnail_canvas = tk.Canvas(self.thumbnail_container, bg='white', 
                                        width=400, height=300)
        self.thumbnail_canvas.pack(expand=True, fill=tk.BOTH)
        
        # Loading frame
        self.loading_frame = ttk.Frame(self.thumbnail_container)
        self.loading_label = ttk.Label(self.loading_frame, text="Generating thumbnail...", 
                                     font=('TkDefaultFont', 10))
        self.loading_label.pack(pady=20)
        
        # Progress bar for loading
        self.loading_progress = ttk.Progressbar(self.loading_frame, mode='indeterminate')
        self.loading_progress.pack(pady=10)
        
        # Thumbnail status at bottom
        self.thumbnail_status = ttk.Label(self.thumbnail_frame, text="Select a file to generate thumbnail")
        self.thumbnail_status.pack(pady=5)
    
    def setup_details_tab(self):
        """Setup file details tab"""
        self.details_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.details_frame, text="Details")
        
        # Scrollable text area for details
        self.details_text = tk.Text(self.details_frame, wrap=tk.WORD, height=20, 
                                   font=('Consolas', 9))
        details_scrollbar = ttk.Scrollbar(self.details_frame, orient=tk.VERTICAL, 
                                         command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scrollbar.set)
        
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
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
        """Preview a file with ICAD thumbnail"""
        self.current_file = file_info
        
        # Update header
        filename = file_info.get('filename', 'Unknown')
        self.filename_label.config(text=filename)
        
        # Enable action buttons
        self.open_btn.config(state=tk.NORMAL)
        self.location_btn.config(state=tk.NORMAL)
        self.refresh_btn.config(state=tk.NORMAL)
        
        # Update footer
        file_size = file_info.get('file_size', 0)
        self.size_label.config(text=self.format_file_size(file_size))
        
        # Update details
        self.update_details()
        
        # Load thumbnail for .icd files
        file_path = file_info.get('file_path', '')
        if file_path and file_path.lower().endswith('.icd'):
            self.load_thumbnail()
        else:
            self.show_file_type_icon()
        
        # Update status
        self.status_label.config(text=f"Previewing: {filename}")
    
    def load_thumbnail(self):
        """Load or generate thumbnail for ICAD file"""
        if not self.current_file:
            return
        
        file_path = self.current_file.get('file_path', '')
        if not file_path or not Path(file_path).exists():
            self.show_error("File not found")
            return
        
        # Check if thumbnail already exists
        thumbnail_path = self.screen_capture.get_thumbnail_path(file_path)
        
        if thumbnail_path and thumbnail_path.exists():
            # Load existing thumbnail
            self.display_thumbnail(str(thumbnail_path))
            self.thumbnail_status.config(text=f"Cached thumbnail: {Path(file_path).name}")
        else:
            # Generate new thumbnail
            self.generate_thumbnail()
    
    def generate_thumbnail(self):
        """Generate thumbnail for current file"""
        if not self.current_file:
            return
        
        file_path = self.current_file.get('file_path', '')
        if not file_path:
            return
        
        # Show loading state
        self.show_loading()
        
        # Cancel any existing thumbnail generation
        if self.thumbnail_worker and self.thumbnail_worker.is_alive():
            return
        
        # Start thumbnail generation in background
        self.thumbnail_worker = ThumbnailWorker(
            file_path,
            self.screen_capture,
            self.on_thumbnail_generated
        )
        self.thumbnail_worker.start()
    
    def show_loading(self):
        """Show loading state"""
        # Clear canvas
        self.thumbnail_canvas.delete("all")
        
        # Show loading frame
        self.loading_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.loading_progress.start()
        self.loading_label.config(text="Generating ICAD thumbnail...")
        
        filename = self.current_file.get('filename', 'file') if self.current_file else 'file'
        self.thumbnail_status.config(text=f"Generating thumbnail for {filename}...")
    
    def on_thumbnail_generated(self, thumbnail_path: str, error: str):
        """Handle thumbnail generation completion"""
        # Hide loading
        self.loading_progress.stop()
        self.loading_frame.place_forget()
        
        if error:
            self.show_error(error)
        elif thumbnail_path:
            self.display_thumbnail(thumbnail_path)
            self.thumbnail_status.config(text=f"Thumbnail generated: {Path(thumbnail_path).name}")
        else:
            self.show_error("Could not generate thumbnail")
    
    def display_thumbnail(self, thumbnail_path: str):
        """Display thumbnail in canvas"""
        try:
            from PIL import Image, ImageTk
            
            # Load thumbnail
            image = Image.open(thumbnail_path)
            
            # Convert to PhotoImage
            self.preview_image = ImageTk.PhotoImage(image)
            
            # Clear canvas and display image
            self.thumbnail_canvas.delete("all")
            
            # Center image in canvas
            canvas_width = self.thumbnail_canvas.winfo_width()
            canvas_height = self.thumbnail_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                x = canvas_width // 2
                y = canvas_height // 2
            else:
                x = 200
                y = 150
            
            self.thumbnail_canvas.create_image(x, y, image=self.preview_image)
            
        except Exception as e:
            self.show_error(f"Error displaying thumbnail: {e}")
    
    def show_file_type_icon(self):
        """Show file type icon for non-ICD files"""
        if not self.current_file:
            return
        
        file_type = self.current_file.get('file_type', '').lower()
        filename = self.current_file.get('filename', 'Unknown')
        
        # Clear canvas
        self.thumbnail_canvas.delete("all")
        
        # Show file type icon
        icon_text = self.get_file_type_icon(file_type)
        description = self.get_file_type_description(file_type)
        
        # Center text in canvas
        self.thumbnail_canvas.create_text(200, 120, text=icon_text, 
                                        font=('TkDefaultFont', 48), fill='gray')
        self.thumbnail_canvas.create_text(200, 180, text=description, 
                                        font=('TkDefaultFont', 12), fill='gray')
        self.thumbnail_canvas.create_text(200, 200, text=filename, 
                                        font=('TkDefaultFont', 10), fill='darkgray')
        
        self.thumbnail_status.config(text=f"File type: {description}")
    
    def show_error(self, error_message: str):
        """Show error in thumbnail area"""
        self.thumbnail_canvas.delete("all")
        self.thumbnail_canvas.create_text(200, 150, text=f"❌ {error_message}", 
                                        font=('TkDefaultFont', 12), fill='red')
        self.thumbnail_status.config(text=f"Error: {error_message}")
    
    def get_file_type_icon(self, file_type: str) -> str:
        """Get emoji icon for file type"""
        icons = {
            '.dwg': '🔧',
            '.dxf': '📐',
            '.icad': '⚙️',
            '.icd': '📋',
            '.ifc': '🏢',
            '.step': '⚙️',
            '.stp': '⚙️',
            '.pdf': '📄',
        }
        return icons.get(file_type, '📄')
    
    def get_file_type_description(self, file_type: str) -> str:
        """Get file type description"""
        descriptions = {
            '.dwg': 'AutoCAD Drawing',
            '.dxf': 'AutoCAD Exchange',
            '.icad': 'ICAD File',
            '.icd': 'ICAD Document',
            '.ifc': 'Industry Foundation Classes',
            '.step': 'STEP 3D Model',
            '.stp': 'STEP 3D Model',
            '.pdf': 'PDF Document',
        }
        return descriptions.get(file_type, f'{file_type.upper()} File')
    
    def refresh_thumbnail(self):
        """Refresh the current thumbnail"""
        if self.current_file:
            file_path = self.current_file.get('file_path', '')
            if file_path:
                # Clear cached thumbnail
                thumbnail_path = self.screen_capture.get_thumbnail_path(file_path)
                if thumbnail_path and thumbnail_path.exists():
                    thumbnail_path.unlink()
                
                # Regenerate thumbnail
                self.load_thumbnail()
    
    def update_details(self):
        """Update file details"""
        if not self.current_file:
            return
        
        # Build details text
        details = self.build_details_text()
        
        # Update details text widget
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, details)
        self.details_text.config(state=tk.DISABLED)
    
    def build_details_text(self) -> str:
        """Build detailed file information text"""
        file_info = self.current_file
        
        # Basic file information
        details = f"📄 {file_info.get('filename', 'Unknown')}\n\n"
        
        # Location
        details += "📁 Location:\n"
        details += f"• Path: {file_info.get('file_path', '')}\n"
        details += f"• Folder: {Path(file_info.get('file_path', '')).parent.name}\n\n"
        
        # File Properties
        details += "📋 File Information:\n"
        details += f"• Type: {self.get_file_type_description(file_info.get('file_type', ''))}\n"
        details += f"• Size: {self.format_file_size(file_info.get('file_size', 0))}\n"
        
        # Timestamps
        modified = file_info.get('modified_time', '')
        if modified:
            if isinstance(modified, str):
                try:
                    dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                    modified_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    modified_str = str(modified)
            else:
                modified_str = str(modified)
            details += f"• Modified: {modified_str}\n"
        
        details += "\n"
        
        # Project Information
        details += "🏗️ Project Information:\n"
        details += f"• Project: {file_info.get('project_name', 'Not detected')}\n"
        details += f"• Job: {file_info.get('job_name', 'Not detected')}\n"
        details += f"• Company: {file_info.get('company_name', 'Not detected')}\n\n"
        
        # Thumbnail Information
        details += "🖼️ Thumbnail Information:\n"
        file_path = file_info.get('file_path', '')
        if file_path and file_path.lower().endswith('.icd'):
            thumbnail_path = self.screen_capture.get_thumbnail_path(file_path)
            if thumbnail_path and thumbnail_path.exists():
                details += f"• Status: Cached\n"
                details += f"• Cache Path: {thumbnail_path}\n"
            else:
                details += f"• Status: Not generated\n"
            details += f"• Cache Directory: {self.screen_capture.cache_dir}\n"
        else:
            details += f"• Status: Not applicable (not an ICD file)\n"
        
        details += "\n"
        
        # Actions
        details += "💡 Actions:\n"
        details += "• Double-click to open file\n"
        details += "• Right-click for more options\n"
        details += "• Use 'Open' button to launch file\n"
        details += "• Use 'Location' button to open folder\n"
        details += "• Use '🔄 Refresh' to regenerate thumbnail\n"
        
        return details
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        size = size_bytes
        i = 0
        
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def show_empty_state(self):
        """Show empty state when no file is selected"""
        self.current_file = None
        
        # Update header
        self.filename_label.config(text="No file selected")
        
        # Disable action buttons
        self.open_btn.config(state=tk.DISABLED)
        self.location_btn.config(state=tk.DISABLED)
        self.refresh_btn.config(state=tk.DISABLED)
        
        # Clear thumbnail canvas
        self.thumbnail_canvas.delete("all")
        self.thumbnail_canvas.create_text(200, 150, text="Select a file to preview", 
                                        font=('TkDefaultFont', 12), fill='gray')
        
        # Update status
        self.thumbnail_status.config(text="No file selected")
        
        # Clear details
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, "Select a file to view details...")
        self.details_text.config(state=tk.DISABLED)
        
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
                    os.startfile(Path(file_path).parent)  # Windows
                except AttributeError:
                    os.system(f'xdg-open "{Path(file_path).parent}"')  # Linux
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to open location: {e}")
            else:
                messagebox.showwarning("File Not Found", "Selected file no longer exists.")
    
    def refresh_preview(self):
        """Refresh the current preview"""
        if self.current_file:
            self.preview_file(self.current_file)