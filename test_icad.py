import subprocess
import sys

def test_icad_detailed():
    print("Testing ICAD command variations...")
    
    commands = [
        ['icad', '/?'],
        ['icad', '/help'],
        ['icad', '-help'],
        ['icad', '/version'],
        ['icad', '/batch'],
        ['icad', '/script'],
        ['icad']  # Just run without parameters
    ]
    
    for cmd in commands:
        try:
            print(f"\n--- Testing: {' '.join(cmd)} ---")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            print(f"Return code: {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("Command timed out (might be GUI opening)")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_icad_detailed()