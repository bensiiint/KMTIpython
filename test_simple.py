print("Testing ICAD Screen Capture...")

try:
    from PIL import Image
    print("✓ Pillow installed")
except ImportError:
    print("✗ Pillow not installed - run: pip install pillow")

try:
    import pyautogui
    print("✓ PyAutoGUI installed")
except ImportError:
    print("✗ PyAutoGUI not installed - run: pip install pyautogui")

try:
    import pygetwindow
    print("✓ PyGetWindow installed")
except ImportError:
    print("✗ PyGetWindow not installed - run: pip install pygetwindow")

# Test ICAD command
import subprocess
try:
    result = subprocess.run(['icad', '/?'], capture_output=True, timeout=3)
    print("✓ ICAD command working")
except:
    print("✗ ICAD command failed")

print("Test complete!")