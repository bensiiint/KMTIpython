import subprocess
import os
from pathlib import Path

def test_icad_batch():
    # Find a test ICD file
    test_files = [
        "test_icad_project/Building_A/Shopping_Mall_MEP_A102_01.icad",
        "test_icad_project/Building_A/Archive/Residential_Complex_Final_SK001_D.icad"
    ]
    
    test_file = None
    for file in test_files:
        if Path(file).exists():
            test_file = file
            break
    
    if not test_file:
        print("No test ICD file found!")
        return
    
    print(f"Testing with file: {test_file}")
    
    # Test different batch modes
    commands = [
        ['icad', '-bs', test_file],
        ['icad', '-bs3', test_file],
        ['icad', '-pipe', test_file],
        ['icad', '-td', test_file],
        ['icad', '-3d', test_file],
        ['icad', '-c', test_file],
        ['icad', '-w', test_file],
    ]
    
    for cmd in commands:
        try:
            print(f"\n--- Testing: {' '.join(cmd)} ---")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print(f"STDOUT: {result.stdout}")
            if result.stderr:
                print(f"STDERR: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("Command timed out - might be opening GUI")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_icad_batch()