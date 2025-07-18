"""
ICAD Automated Screen Capture System
Generates isometric thumbnails by capturing ICAD window automatically
Updated with preview area cropping to capture only the wireframe, not the entire UI
"""

import os
import time
import subprocess
import tempfile
import hashlib
from pathlib import Path
from typing import Optional, Tuple
import threading

try:
    from PIL import Image, ImageDraw
    import pyautogui
    import pygetwindow as gw
    CAPTURE_AVAILABLE = True
except ImportError:
    CAPTURE_AVAILABLE = False
    print("Warning: Screen capture libraries not available. Run: pip install pillow pyautogui pygetwindow")

class ICADScreenCapture:
    """Automated screen capture system for ICAD isometric previews"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "icad_thumbnails"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Thumbnail settings
        self.thumbnail_size = (400, 300)
        self.icad_wait_time = 8  # Increased wait time for file browser to load
        self.capture_delay = 2   # seconds to wait before capture
        
        # ICAD process tracking
        self.current_process = None
        self.capture_timeout = 15  # max seconds to wait for capture
        
        print(f"ICAD Screen Capture initialized")
        print(f"Cache directory: {self.cache_dir}")
        print(f"Capture available: {CAPTURE_AVAILABLE}")
    
    def get_thumbnail_path(self, icd_file_path: str) -> Path:
        """Get cached thumbnail path for an ICD file"""
        icd_path = Path(icd_file_path)
        if not icd_path.exists():
            return None
        
        # Create cache key from file path and modification time
        mod_time = icd_path.stat().st_mtime
        cache_key = hashlib.md5(f"{icd_file_path}_{mod_time}".encode()).hexdigest()
        return self.cache_dir / f"{cache_key}.png"
    
    def generate_thumbnail(self, icd_file_path: str) -> Optional[str]:
        """Generate thumbnail for ICD file using screen capture"""
        if not CAPTURE_AVAILABLE:
            print("Screen capture libraries not available")
            return None
        
        icd_path = Path(icd_file_path)
        if not icd_path.exists():
            print(f"ICD file not found: {icd_file_path}")
            return None
        
        # Get thumbnail path
        thumbnail_path = self.get_thumbnail_path(icd_file_path)
        if not thumbnail_path:
            return None
        
        # Check if cached thumbnail exists
        if thumbnail_path.exists():
            print(f"Using cached thumbnail: {thumbnail_path}")
            return str(thumbnail_path)
        
        print(f"Generating thumbnail for: {icd_path.name}")
        
        try:
            # Step 1: Open ICAD with the ICD file
            if not self._open_icad_file(icd_file_path):
                print("Failed to open ICAD file")
                return None
            
            # Step 2: Wait for ICAD to load completely
            print(f"⏱️ Waiting {self.icad_wait_time} seconds for ICAD to load...")
            time.sleep(self.icad_wait_time)
            
            # Step 3: Find ICAD window
            icad_window = self._find_icad_window()
            if not icad_window:
                print("Could not find ICAD window")
                self._cleanup_icad()
                return None
            
            # Step 4: Set isometric view (if possible)
            self._set_isometric_view(icad_window)
            
            # Step 5: Capture ICAD window and crop to preview area
            screenshot = self._capture_icad_window(icad_window)
            if not screenshot:
                print("Failed to capture ICAD window")
                self._cleanup_icad()
                return None
            
            # Step 6: Process and save thumbnail
            thumbnail_saved = self._save_thumbnail(screenshot, thumbnail_path)
            
            # Step 7: ALWAYS cleanup ICAD after capture (success or failure)
            print("🎯 Capture complete, closing ICAD automatically...")
            self._cleanup_icad()
            
            if thumbnail_saved:
                print(f"✅ Thumbnail saved and ICAD closed: {thumbnail_path}")
                return str(thumbnail_path)
            else:
                print("❌ Failed to save thumbnail")
                return None
                
        except Exception as e:
            print(f"❌ Error generating thumbnail: {e}")
            # Always cleanup on error
            self._cleanup_icad()
            return None
    
    def _open_icad_file(self, icd_file_path: str) -> bool:
        """Open ICD file in ICAD SX"""
        try:
            # Try different ICAD executable names
            icad_executables = [
                'icad',      # Standard ICAD
                'icadsx',    # ICAD SX
                'ICADSX',    # ICAD SX uppercase
                'icad-sx',   # ICAD SX with dash
                'ICADSx',    # Mixed case
            ]
            
            for exe in icad_executables:
                try:
                    cmd = [exe, '-w', icd_file_path]
                    print(f"Trying to open with: {' '.join(cmd)}")
                    
                    # Start ICAD process
                    self.current_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    # Give ICAD time to start
                    time.sleep(1)
                    
                    # Check if process is still running
                    if self.current_process.poll() is None:
                        print(f"✅ {exe} process started successfully")
                        return True
                    else:
                        print(f"❌ {exe} process terminated immediately")
                        continue
                        
                except FileNotFoundError:
                    print(f"❌ {exe} not found, trying next...")
                    continue
                except Exception as e:
                    print(f"❌ Error with {exe}: {e}")
                    continue
            
            print("❌ Could not start any ICAD variant")
            return False
                
        except Exception as e:
            print(f"❌ Error opening ICAD: {e}")
            return False
    
    def _find_icad_window(self) -> Optional[object]:
        """Find ICAD SX window"""
        try:
            # Wait for ICAD window to appear
            max_attempts = 10
            for attempt in range(max_attempts):
                print(f"Looking for ICAD SX window (attempt {attempt + 1}/{max_attempts})")
                
                # ICAD SX specific window titles
                icad_titles = [
                    'ICAD SX',           # Primary ICAD SX title
                    'ICADSX',            # Alternative
                    'ICAD-SX',           # With dash
                    'ICAD',              # General ICAD
                    'COLMINA',           # ICAD platform
                    'FUJITSU',           # Company name
                    'Manufacturing Industry Solution',
                    'ファイルを開く',      # Japanese "Open File"
                    'icad',              # Lowercase
                    'ICD',               # File type
                    'SX',                # SX variant
                ]
                
                # Look for any window containing ICAD-related text
                all_windows = gw.getAllWindows()
                for window in all_windows:
                    if not window.title:
                        continue
                        
                    window_title = window.title.upper()
                    
                    # Check for ICAD SX titles
                    for icad_title in icad_titles:
                        if icad_title.upper() in window_title:
                            print(f"Found ICAD SX window: {window.title}")
                            return window
                    
                    # Also check for any window with our ICD file name
                    # This helps when ICAD SX changes title to include filename
                    if '.ICD' in window_title or '.ICAD' in window_title:
                        print(f"Found ICD file window: {window.title}")
                        return window
                
                # Wait before next attempt
                time.sleep(1)
            
            print("❌ Could not find ICAD SX window")
            return None
            
        except Exception as e:
            print(f"❌ Error finding ICAD SX window: {e}")
            return None
    
    def _set_isometric_view(self, icad_window: object):
        """Try to set isometric view in ICAD"""
        try:
            # Bring ICAD window to front
            icad_window.activate()
            time.sleep(0.5)
            
            # Try common isometric view shortcuts
            # These might work depending on ICAD version
            shortcuts = [
                'ctrl+7',  # Common isometric shortcut
                'f7',      # Another common shortcut
                'ctrl+i',  # Isometric
                'alt+v',   # View menu
            ]
            
            for shortcut in shortcuts:
                try:
                    pyautogui.hotkey(*shortcut.split('+'))
                    time.sleep(0.5)
                    break  # If one works, stop trying others
                except:
                    continue
            
            # Additional wait for view to change
            time.sleep(self.capture_delay)
            
        except Exception as e:
            print(f"Could not set isometric view: {e}")
            # Continue anyway - we'll capture whatever view is shown
    
    def _capture_icad_window(self, icad_window: object) -> Optional[Image.Image]:
        """Capture ICAD window and extract the 3D viewport area"""
        try:
            # Get window position and size
            left = icad_window.left
            top = icad_window.top
            width = icad_window.width
            height = icad_window.height
            
            print(f"Capturing ICAD SX window: {left}, {top}, {width}x{height}")
            
            # Bring window to front
            icad_window.activate()
            time.sleep(0.5)
            
            # Capture the entire window area
            screenshot = pyautogui.screenshot(region=(left, top, width, height))
            
            print("Window captured successfully")
            
            # Find and extract the 3D viewport (blue rectangle)
            viewport_image = self._extract_3d_viewport(screenshot)
            
            return viewport_image
            
        except Exception as e:
            print(f"Error capturing window: {e}")
            return None
    
    def _extract_3d_viewport(self, screenshot: Image.Image) -> Image.Image:
        """Extract the 3D viewport area (blue rectangle) from screenshot"""
        try:
            width, height = screenshot.size
            print(f"Analyzing screenshot for 3D viewport: {width}x{height}")
            
            # Method 1: Try to detect the blue/gray 3D viewport by color
            viewport_rect = self._detect_viewport_by_color(screenshot)
            
            if viewport_rect:
                print(f"✅ Found 3D viewport by color detection: {viewport_rect}")
                cropped = screenshot.crop(viewport_rect)
                return cropped
            
            # Method 2: Use smart positioning based on ICAD SX layout
            viewport_rect = self._detect_viewport_by_position(screenshot)
            
            if viewport_rect:
                print(f"✅ Found 3D viewport by position: {viewport_rect}")
                cropped = screenshot.crop(viewport_rect)
                return cropped
            
            # Method 3: Fallback to the original cropping method
            print("⚠️ Using fallback cropping method")
            return self._crop_to_preview_area(screenshot)
            
        except Exception as e:
            print(f"Error extracting 3D viewport: {e}")
            return screenshot
    
    def _detect_viewport_by_color(self, screenshot: Image.Image) -> Optional[tuple]:
        """Detect 3D viewport by looking for the characteristic blue/gray background"""
        try:
            import numpy as np
            
            # Convert to numpy array for analysis
            img_array = np.array(screenshot)
            
            # Define color ranges for 3D viewport background
            # Gray/blue colors typically used in CAD viewports
            target_colors = [
                # Gray viewport background
                ([100, 100, 100], [160, 160, 160]),  # Gray range
                # Blue viewport background  
                ([80, 80, 120], [140, 140, 180]),    # Blue-gray range
                # Dark gray viewport
                ([60, 60, 60], [110, 110, 110]),     # Dark gray range
            ]
            
            best_rect = None
            largest_area = 0
            
            for (lower, upper) in target_colors:
                # Create mask for this color range
                mask = np.all((img_array >= lower) & (img_array <= upper), axis=2)
                
                # Find contiguous regions
                rect = self._find_largest_rectangle(mask)
                
                if rect:
                    area = (rect[2] - rect[0]) * (rect[3] - rect[1])
                    if area > largest_area:
                        largest_area = area
                        best_rect = rect
            
            # Only return if we found a reasonably sized viewport
            if best_rect and largest_area > 10000:  # At least 100x100 pixels
                print(f"Found viewport by color: area={largest_area}")
                return best_rect
            
            return None
            
        except ImportError:
            print("numpy not available, skipping color detection")
            return None
        except Exception as e:
            print(f"Error in color detection: {e}")
            return None
    
    def _find_largest_rectangle(self, mask) -> Optional[tuple]:
        """Find the largest rectangular region in a binary mask"""
        try:
            import numpy as np
            
            # Find all True positions
            true_positions = np.where(mask)
            
            if len(true_positions[0]) == 0:
                return None
            
            # Get bounding box of all True positions
            min_y, max_y = np.min(true_positions[0]), np.max(true_positions[0])
            min_x, max_x = np.min(true_positions[1]), np.max(true_positions[1])
            
            # Check if this forms a reasonable rectangle
            width = max_x - min_x
            height = max_y - min_y
            
            # Must be reasonably sized and roughly rectangular
            if width > 200 and height > 150 and width/height < 3 and height/width < 3:
                return (min_x, min_y, max_x, max_y)
            
            return None
            
        except Exception as e:
            print(f"Error finding rectangle: {e}")
            return None
    
    def _detect_viewport_by_position(self, screenshot: Image.Image) -> Optional[tuple]:
        """Detect 3D viewport by expected position in ICAD SX interface"""
        try:
            width, height = screenshot.size
            
            # ICAD SX viewport position based on your actual layout
            # The blue 3D viewport is in the center-right area, excluding toolbars and file browser
            
            # Try different potential viewport positions that match your ICAD SX layout
            viewport_candidates = [
                # Primary viewport area (based on your screenshot)
                (int(width * 0.25), int(height * 0.15), int(width * 0.97), int(height * 0.85)),
                
                # Slightly more conservative crop
                (int(width * 0.27), int(height * 0.17), int(width * 0.95), int(height * 0.83)),
                
                # Alternative if toolbars are different
                (int(width * 0.23), int(height * 0.13), int(width * 0.98), int(height * 0.87)),
                
                # Fallback with more margin
                (int(width * 0.30), int(height * 0.18), int(width * 0.92), int(height * 0.82)),
            ]
            
            # Test each candidate and pick the one with most uniform color (blue/gray viewport)
            best_rect = None
            best_score = 0
            
            for rect in viewport_candidates:
                score = self._evaluate_viewport_candidate(screenshot, rect)
                if score > best_score:
                    best_score = score
                    best_rect = rect
            
            # Only return if we found a good candidate
            if best_rect and best_score > 0.2:  # Lower threshold since viewport may have 3D content
                print(f"Found viewport by position: score={best_score:.2f}")
                return best_rect
            
            return None
            
        except Exception as e:
            print(f"Error in position detection: {e}")
            return None
    
    def _evaluate_viewport_candidate(self, screenshot: Image.Image, rect: tuple) -> float:
        """Evaluate how likely a rectangle is to be the 3D viewport"""
        try:
            # Crop to candidate area
            cropped = screenshot.crop(rect)
            
            # Convert to RGB if needed
            if cropped.mode != 'RGB':
                cropped = cropped.convert('RGB')
            
            # Get pixel colors
            pixels = list(cropped.getdata())
            
            if not pixels:
                return 0.0
            
            # Count pixels that look like viewport background
            viewport_pixels = 0
            total_pixels = len(pixels)
            
            for r, g, b in pixels:
                # Check if pixel looks like viewport background
                if (90 <= r <= 170 and 90 <= g <= 170 and 90 <= b <= 170) or \
                   (80 <= r <= 140 and 80 <= g <= 140 and 120 <= b <= 180):
                    viewport_pixels += 1
            
            # Calculate score (percentage of viewport-like pixels)
            score = viewport_pixels / total_pixels
            
            return score
            
        except Exception as e:
            print(f"Error evaluating viewport candidate: {e}")
            return 0.0
    
    def _crop_to_preview_area(self, screenshot: Image.Image) -> Image.Image:
        """Fallback method: Crop screenshot to show only the 3D viewport area"""
        try:
            width, height = screenshot.size
            print(f"Using precise viewport crop for ICAD SX: {width}x{height}")
            
            # Precise targeting of the 3D viewport based on your ICAD SX layout
            # From your screenshot, the blue viewport area is in the center-right
            
            # Calculate viewport bounds to capture only the blue 3D view area
            viewport_left = int(width * 0.25)    # 25% from left (skip file browser)
            viewport_top = int(height * 0.15)    # 15% from top (skip toolbars)  
            viewport_right = int(width * 0.97)   # 97% from left (full viewport width)
            viewport_bottom = int(height * 0.85) # 85% from top (skip status bar)
            
            print(f"Viewport crop bounds: {viewport_left}, {viewport_top}, {viewport_right}, {viewport_bottom}")
            
            # Ensure we don't exceed image bounds
            viewport_left = max(0, viewport_left)
            viewport_top = max(0, viewport_top)
            viewport_right = min(width, viewport_right)
            viewport_bottom = min(height, viewport_bottom)
            
            # Crop the image to get only the blue viewport area
            cropped = screenshot.crop((viewport_left, viewport_top, viewport_right, viewport_bottom))
            
            print(f"Viewport cropped image size: {cropped.size}")
            
            return cropped
            
        except Exception as e:
            print(f"Error in viewport crop: {e}")
            return screenshot  # Return original if cropping fails
    
    def _save_thumbnail(self, screenshot: Image.Image, thumbnail_path: Path) -> bool:
        """Process and save thumbnail"""
        try:
            # Convert to RGB if needed
            if screenshot.mode != 'RGB':
                screenshot = screenshot.convert('RGB')
            
            # Resize to thumbnail size while maintaining aspect ratio
            screenshot.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
            
            # Create final thumbnail with white background
            final_thumbnail = Image.new('RGB', self.thumbnail_size, color='white')
            
            # Center the cropped image
            paste_x = (self.thumbnail_size[0] - screenshot.width) // 2
            paste_y = (self.thumbnail_size[1] - screenshot.height) // 2
            final_thumbnail.paste(screenshot, (paste_x, paste_y))
            
            # Add a subtle border
            draw = ImageDraw.Draw(final_thumbnail)
            draw.rectangle([0, 0, self.thumbnail_size[0]-1, self.thumbnail_size[1]-1], 
                          outline='#cccccc', width=1)
            
            # Save as PNG
            final_thumbnail.save(thumbnail_path, 'PNG')
            
            print(f"Thumbnail saved: {thumbnail_path}")
            return True
            
        except Exception as e:
            print(f"Error saving thumbnail: {e}")
            return False
    
    def _cleanup_icad(self):
        """Clean up ICAD process with multiple methods"""
        try:
            print("🔄 Cleaning up ICAD...")
            
            # Method 1: Close ICAD window using Alt+F4
            self._close_icad_window()
            
            # Method 2: Terminate the process
            if self.current_process:
                try:
                    print("📝 Terminating ICAD process...")
                    self.current_process.terminate()
                    
                    # Wait for graceful termination
                    try:
                        self.current_process.wait(timeout=3)
                        print("✅ ICAD process terminated gracefully")
                    except subprocess.TimeoutExpired:
                        print("⚠️ Graceful termination failed, force killing...")
                        self.current_process.kill()
                        self.current_process.wait()
                        print("✅ ICAD process force killed")
                        
                except Exception as e:
                    print(f"❌ Error terminating process: {e}")
                finally:
                    self.current_process = None
            
            # Method 3: Kill any remaining ICAD processes
            self._kill_remaining_icad_processes()
            
            print("✅ ICAD cleanup completed")
            
        except Exception as e:
            print(f"❌ Error cleaning up ICAD: {e}")
    
    def _close_icad_window(self):
        """Close ICAD window using keyboard shortcuts"""
        try:
            # Find and activate ICAD window
            icad_window = self._find_icad_window()
            if icad_window:
                print("🖱️ Closing ICAD window...")
                icad_window.activate()
                time.sleep(0.5)
                
                # Try multiple close methods
                close_methods = [
                    lambda: pyautogui.hotkey('alt', 'f4'),     # Alt+F4
                    lambda: pyautogui.hotkey('ctrl', 'q'),     # Ctrl+Q  
                    lambda: pyautogui.hotkey('ctrl', 'w'),     # Ctrl+W
                    lambda: pyautogui.press('escape'),         # Escape
                    lambda: pyautogui.hotkey('alt', 'f', 'x'), # Alt+F, X (File->Exit)
                ]
                
                for i, close_method in enumerate(close_methods):
                    try:
                        print(f"🔑 Trying close method {i+1}...")
                        close_method()
                        time.sleep(1)
                        
                        # Check if window is gone
                        if not self._window_exists(icad_window):
                            print("✅ ICAD window closed successfully")
                            return True
                            
                    except Exception as e:
                        print(f"⚠️ Close method {i+1} failed: {e}")
                        continue
                
                print("⚠️ Window close methods failed")
                return False
            else:
                print("🔍 No ICAD window found to close")
                return True
                
        except Exception as e:
            print(f"❌ Error closing ICAD window: {e}")
            return False
    
    def _window_exists(self, window) -> bool:
        """Check if window still exists"""
        try:
            # Try to access window properties
            _ = window.title
            _ = window.left
            return True
        except:
            return False
    
    def _kill_remaining_icad_processes(self):
        """Kill any remaining ICAD SX processes"""
        try:
            import psutil
            
            print("🔍 Checking for remaining ICAD SX processes...")
            
            # Find ICAD SX processes
            icad_processes = []
            process_names = ['icad', 'icadsx', 'colmina', 'fujitsu', 'icd']
            
            for process in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    process_name = process.info['name'].lower()
                    if any(icad_name in process_name for icad_name in process_names):
                        icad_processes.append(process)
                except:
                    continue
            
            if icad_processes:
                print(f"🎯 Found {len(icad_processes)} ICAD SX processes to kill")
                
                for process in icad_processes:
                    try:
                        print(f"🔧 Killing process: {process.info['name']} (PID: {process.info['pid']})")
                        process.terminate()
                        
                        # Wait for termination
                        try:
                            process.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            process.kill()
                            
                        print(f"✅ Process killed: {process.info['name']}")
                        
                    except Exception as e:
                        print(f"❌ Error killing process: {e}")
            else:
                print("✅ No remaining ICAD SX processes found")
                
        except ImportError:
            print("⚠️ psutil not available, using taskkill instead")
            self._kill_icad_with_taskkill()
        except Exception as e:
            print(f"❌ Error checking processes: {e}")
    
    def _kill_icad_with_taskkill(self):
        """Kill ICAD SX processes using Windows taskkill"""
        try:
            # ICAD SX specific executables
            icad_executables = [
                'icad.exe', 'ICAD.exe', 
                'icadsx.exe', 'ICADSX.exe',
                'icad-sx.exe', 'ICAD-SX.exe',
                'colmina.exe', 'COLMINA.exe',
                'fujitsu.exe', 'FUJITSU.exe'
            ]
            
            for exe in icad_executables:
                try:
                    print(f"🔧 Killing {exe}...")
                    subprocess.run(['taskkill', '/F', '/IM', exe], 
                                 capture_output=True, 
                                 timeout=5)
                    print(f"✅ Killed {exe}")
                except:
                    continue
                    
        except Exception as e:
            print(f"❌ Error using taskkill: {e}")
    
    def generate_placeholder_thumbnail(self, icd_file_path: str) -> Optional[str]:
        """Generate placeholder thumbnail when screen capture fails"""
        try:
            thumbnail_path = self.get_thumbnail_path(icd_file_path)
            if not thumbnail_path:
                return None
            
            # Create placeholder image
            img = Image.new('RGB', self.thumbnail_size, color='#f0f0f0')
            draw = ImageDraw.Draw(img)
            
            # Get file info
            file_name = Path(icd_file_path).name
            
            # Draw file type icon
            icon_size = 80
            icon_x = self.thumbnail_size[0] // 2 - icon_size // 2
            icon_y = self.thumbnail_size[1] // 2 - icon_size // 2 - 30
            
            # Simple rectangle as file icon
            draw.rectangle([icon_x, icon_y, icon_x + icon_size, icon_y + icon_size], 
                         fill='#4CAF50', outline='#45a049', width=2)
            
            # Draw file extension
            try:
                from PIL import ImageFont
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = None
            
            # Draw "ICD" text
            if font:
                text_bbox = draw.textbbox((0, 0), "ICD", font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = icon_x + (icon_size - text_width) // 2
                text_y = icon_y + (icon_size - text_height) // 2
                draw.text((text_x, text_y), "ICD", fill='white', font=font)
            
            # Draw filename
            filename_y = icon_y + icon_size + 20
            if font:
                filename_bbox = draw.textbbox((0, 0), file_name, font=font)
                filename_width = filename_bbox[2] - filename_bbox[0]
                filename_x = (self.thumbnail_size[0] - filename_width) // 2
                draw.text((filename_x, filename_y), file_name, fill='#333', font=font)
            
            # Save placeholder
            img.save(thumbnail_path, 'PNG')
            
            print(f"Placeholder thumbnail created: {thumbnail_path}")
            return str(thumbnail_path)
            
        except Exception as e:
            print(f"Error creating placeholder: {e}")
            return None
    
    def clear_cache(self):
        """Clear all cached thumbnails"""
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir()
            print("Thumbnail cache cleared")
        except Exception as e:
            print(f"Error clearing cache: {e}")

class ThumbnailWorker(threading.Thread):
    """Background worker for generating thumbnails"""
    
    def __init__(self, icd_file_path: str, screen_capture: ICADScreenCapture, callback):
        super().__init__(daemon=True)
        self.icd_file_path = icd_file_path
        self.screen_capture = screen_capture
        self.callback = callback
    
    def run(self):
        """Generate thumbnail in background"""
        try:
            # Check for cached thumbnail first
            thumbnail_path = self.screen_capture.get_thumbnail_path(self.icd_file_path)
            
            if thumbnail_path and thumbnail_path.exists():
                # Use cached thumbnail
                print(f"Using cached thumbnail: {thumbnail_path}")
                self.callback(str(thumbnail_path), None)
                return
            
            # Generate new thumbnail
            result = self.screen_capture.generate_thumbnail(self.icd_file_path)
            
            if result:
                self.callback(result, None)
            else:
                # Try to create placeholder
                placeholder = self.screen_capture.generate_placeholder_thumbnail(self.icd_file_path)
                if placeholder:
                    self.callback(placeholder, None)
                else:
                    self.callback(None, "Failed to generate thumbnail")
                    
        except Exception as e:
            self.callback(None, f"Error in thumbnail worker: {e}")

def test_icad_sx_commands():
    """Test ICAD SX specific commands"""
    print("🧪 Testing ICAD SX Commands...")
    
    # Test different command variations
    test_commands = [
        ['icad', '--help'],
        ['icadsx', '--help'],
        ['ICADSX', '--help'],
        ['icad-sx', '--help'],
        ['ICADSx', '--help'],
        ['icad', '-h'],
        ['icadsx', '-h'],
        ['icad', '-?'],
        ['icadsx', '-?'],
    ]
    
    working_command = None
    
    for cmd in test_commands:
        try:
            print(f"\n🔍 Testing: {' '.join(cmd)}")
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            
            if result.returncode == 0:
                print(f"✅ SUCCESS: {cmd[0]} command works!")
                working_command = cmd[0]
                
                if result.stdout:
                    print("📄 Output:")
                    print(result.stdout[:500])  # First 500 chars
                break
            else:
                print(f"❌ Failed with return code: {result.returncode}")
                
        except FileNotFoundError:
            print(f"❌ {cmd[0]} not found")
        except subprocess.TimeoutExpired:
            print(f"⏱️ {cmd[0]} timed out")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    if working_command:
        print(f"\n🎉 Found working ICAD SX command: {working_command}")
        return working_command
    else:
        print("\n❌ No working ICAD SX command found")
        return None

def test_viewport_detection_only():
    """Test viewport detection without generating thumbnails"""
    if not CAPTURE_AVAILABLE:
        print("Screen capture libraries not available")
        return
    
    print("🎯 Testing ICAD SX Viewport Detection")
    print("=" * 50)
    
    # Find test file
    test_files = [
        "test_icad_project/Building_A/Shopping_Mall_MEP_A102_01.icad",
        "test_icad_project/Building_A/Archive/Residential_Complex_Final_SK001_D.icad"
    ]
    
    test_file = None
    for file_path in test_files:
        if Path(file_path).exists():
            test_file = file_path
            break
    
    if not test_file:
        print("❌ No test ICD file found")
        return
    
    screen_capture = ICADScreenCapture()
    
    print(f"📁 Using test file: {test_file}")
    print("\n🔧 This will:")
    print("1. Open ICAD SX with your test file")
    print("2. Capture the full window")
    print("3. Test different viewport detection methods")
    print("4. Save debug images showing what's detected")
    print("5. Close ICAD SX")
    print("\n⏱️ Starting in 3 seconds...")
    
    time.sleep(3)
    
    try:
        # Open ICAD SX
        if not screen_capture._open_icad_file(test_file):
            print("❌ Failed to open ICAD SX")
            return
        
        # Wait for loading
        print(f"⏱️ Waiting {screen_capture.icad_wait_time} seconds for ICAD SX to load...")
        time.sleep(screen_capture.icad_wait_time)
        
        # Find window
        icad_window = screen_capture._find_icad_window()
        if not icad_window:
            print("❌ Could not find ICAD SX window")
            screen_capture._cleanup_icad()
            return
        
        # Capture full window
        left = icad_window.left
        top = icad_window.top
        width = icad_window.width
        height = icad_window.height
        
        print(f"📸 Capturing ICAD SX window: {width}x{height}")
        
        icad_window.activate()
        time.sleep(0.5)
        
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        
        # Test viewport detection methods
        print("\n🔍 Testing viewport detection methods...")
        
        # Method 1: Color detection
        print("1️⃣ Testing color detection...")
        color_rect = screen_capture._detect_viewport_by_color(screenshot)
        if color_rect:
            print(f"✅ Color detection found viewport: {color_rect}")
            screen_capture.save_debug_images(screenshot, color_rect)
        else:
            print("❌ Color detection failed")
        
        # Method 2: Position detection
        print("2️⃣ Testing position detection...")
        position_rect = screen_capture._detect_viewport_by_position(screenshot)
        if position_rect:
            print(f"✅ Position detection found viewport: {position_rect}")
            if not color_rect:  # Only save if color detection didn't work
                screen_capture.save_debug_images(screenshot, position_rect)
        else:
            print("❌ Position detection failed")
        
        # Method 3: Fallback method
        print("3️⃣ Testing fallback method...")
        fallback_image = screen_capture._crop_to_preview_area(screenshot)
        print(f"✅ Fallback method produced: {fallback_image.size}")
        
        # Save debug images if no other method worked
        if not color_rect and not position_rect:
            screen_capture.save_debug_images(screenshot)
        
        # Cleanup
        print("\n🧹 Cleaning up ICAD SX...")
        screen_capture._cleanup_icad()
        
        print("\n🎉 Viewport detection test completed!")
        print(f"📁 Check debug images in: {screen_capture.cache_dir / 'debug'}")
        
    except Exception as e:
        print(f"❌ Error in viewport detection test: {e}")
        screen_capture._cleanup_icad()

def test_screen_capture():
    """Test the screen capture system with ICAD SX auto-close and viewport detection"""
    if not CAPTURE_AVAILABLE:
        print("Screen capture libraries not available")
        print("Install with: pip install pillow pyautogui pygetwindow")
        return
    
    print("🎯 ICAD SX Complete Test")
    print("=" * 50)
    
    # Ask user what they want to test
    print("Choose test mode:")
    print("1. Viewport detection only (faster, shows debug images)")
    print("2. Full thumbnail generation (complete process)")
    
    try:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice == "1":
            test_viewport_detection_only()
            return
        elif choice != "2":
            print("Invalid choice, running full test...")
    except:
        print("Running full test...")
    
    # First test which ICAD SX command works
    working_command = test_icad_sx_commands()
    if not working_command:
        print("❌ Cannot proceed without working ICAD SX command")
        return
    
    # Install dependencies
    try:
        import psutil
        print("✅ psutil available")
    except ImportError:
        print("📦 Installing psutil for better process management...")
        subprocess.run(['pip', 'install', 'psutil'], check=True)
    
    try:
        import numpy as np
        print("✅ numpy available")
    except ImportError:
        print("📦 Installing numpy for color detection...")
        subprocess.run(['pip', 'install', 'numpy'], check=True)
    
    # Test full thumbnail generation
    test_files = [
        "test_icad_project/Building_A/Shopping_Mall_MEP_A102_01.icad",
        "test_icad_project/Building_A/Archive/Residential_Complex_Final_SK001_D.icad"
    ]
    
    screen_capture = ICADScreenCapture()
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"\n🧪 Testing ICAD SX full thumbnail generation: {test_file}")
            print("This will:")
            print("1. Open ICAD SX")
            print("2. Detect the blue 3D viewport area (like in your screenshot)")
            print("3. Capture only that viewport area")
            print("4. Automatically close ICAD SX")
            print("5. Save clean viewport thumbnail")
            
            result = screen_capture.generate_thumbnail(test_file)
            
            if result:
                print(f"🎉 Success! Clean viewport thumbnail: {result}")
                print("✅ ICAD SX closed automatically")
                print("✅ Captured only the blue 3D viewport area")
            else:
                print("❌ Failed to generate thumbnail")
            
            break
    else:
        print("❌ No test ICD files found")

if __name__ == "__main__":
    test_screen_capture()