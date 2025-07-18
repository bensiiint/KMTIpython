import subprocess
import os
from pathlib import Path
import time

def test_icad_export():
    test_file = "test_icad_project/Building_A/Shopping_Mall_MEP_A102_01.icad"
    
    if not Path(test_file).exists():
        print(f"Test file not found: {test_file}")
        return
    
    print(f"Testing ICAD export with: {test_file}")
    
    # Record files before
    current_dir = Path(".")
    test_dir = Path("test_icad_project/Building_A/")
    
    before_files = set(current_dir.glob("*"))
    before_test_files = set(test_dir.glob("*"))
    
    print("Running ICAD commands...")
    
    # Try different approaches
    commands = [
        # Try batch mode with different parameters
        ['icad', '-bs', test_file],
        ['icad', '-bs3', test_file],
        ['icad', '-3d', test_file],
        
        # Try with console output
        ['icad', '-c', test_file],
        ['icad', '-w', test_file],
        
        # Try with macro parameter
        ['icad', '-MAC', '1', test_file],
        ['icad', '-PARM', '1', test_file],
    ]
    
    for i, cmd in enumerate(commands):
        try:
            print(f"\n--- Test {i+1}: {' '.join(cmd)} ---")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            print(f"Return code: {result.returncode}")
            
            # Check for new files
            time.sleep(1)  # Give time for file creation
            
            after_files = set(current_dir.glob("*"))
            after_test_files = set(test_dir.glob("*"))
            
            new_files = (after_files - before_files) | (after_test_files - before_test_files)
            
            if new_files:
                print(f"New files created: {[str(f) for f in new_files]}")
            else:
                print("No new files detected")
                
        except subprocess.TimeoutExpired:
            print("Command timed out")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_icad_export()