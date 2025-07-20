import os
import shutil
import subprocess
import sys

# Define paths (adjust these based on your actual structure)
# This script should be in the directory with pyproject.toml
# README_SOURCE_RELATIVE: Relative path from this script's location to your actual README.md
README_SOURCE_RELATIVE = os.path.join("..", "..", "README.md")
LICENSE_SOURCE_RELATIVE = os.path.join("..", "..", "LICENSE") # If your LICENSE is also outside

# Destination files in the current PyPI project root
README_DEST = "README.md"
LICENSE_DEST = "LICENSE"

def run_command(command):
    try:
        # shell=True is sometimes convenient but can be a security risk with untrusted input
        # For simple commands like 'python -m build', it's usually fine.
        # Otherwise, pass command as a list of strings: subprocess.run([sys.executable, "-m", "build"])
        subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
        print(f"Command '{command}' executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error executing command '{command}':")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        raise

def main():
    # --- Pre-build steps ---
    print(f"Copying {README_SOURCE_RELATIVE} and {LICENSE_SOURCE_RELATIVE} to project root for build...")
    
    try:
        shutil.copy2(os.path.abspath(README_SOURCE_RELATIVE), README_DEST)
        shutil.copy2(os.path.abspath(LICENSE_SOURCE_RELATIVE), LICENSE_DEST)
        print("Files copied successfully.")
    except FileNotFoundError as e:
        print(f"Error: Source file not found: {e}")
        return
    except Exception as e:
        print(f"Error copying files: {e}")
        return

    try:
        # --- Build the package ---
        print("Building Python package...")
        run_command(f"{sys.executable} -m build")

        # --- Upload to PyPI (or TestPyPI) ---
        print("Uploading package to PyPI...")
        # Use '--repository testpypi' for testing:
        # run_command(f"{sys.executable} -m twine upload --repository testpypi dist/*")
        run_command(f"{sys.executable} -m twine upload dist/*")

    except Exception as e:
        print(f"An error occurred during build or upload: {e}")
    finally:
        # --- Post-upload steps ---
        print(f"Cleaning up copied {README_DEST} and {LICENSE_DEST}...")
        if os.path.exists(README_DEST):
            os.remove(README_DEST)
        if os.path.exists(LICENSE_DEST):
            os.remove(LICENSE_DEST)
        print("Cleanup complete.")

if __name__ == "__main__":
    main()