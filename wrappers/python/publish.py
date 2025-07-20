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

def run_command(command, description="Executing command"):
    print(f"\n--- {description}: {command} ---")
    try:
        process = subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
        print("Command executed successfully.")
        print("--- Standard Output ---")
        if process.stdout:
            print(process.stdout)
        else:
            print("[No stdout]")
        print("--- End Standard Output ---\n")
    except subprocess.CalledProcessError as e:
        print(f"!!! Error: Command failed with exit code {e.returncode} !!!")
        print(f"Command attempted: '{command}'")
        print("--- Standard Output (on error) ---")
        if e.stdout:
            print(e.stdout)
        else:
            print("[No stdout]")
        print("--- End Standard Output ---\n")
        print("--- Standard Error (on error) ---")
        if e.stderr:
            print(e.stderr)
        else:
            print("[No stderr]")
        print("--- End Standard Error ---\n")
        raise # Re-raise the exception to stop the script

def main():
    print("\n--- Starting PyPI Publishing Process ---")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Expected README source: {os.path.abspath(README_SOURCE_RELATIVE)}")
    print(f"Expected LICENSE source: {os.path.abspath(LICENSE_SOURCE_RELATIVE)}")
    print(f"Temporary README destination: {os.path.abspath(README_DEST)}")
    print(f"Temporary LICENSE destination: {os.path.abspath(LICENSE_DEST)}\n")

    # --- Pre-build steps ---
    print("--- Step 1: Copying README.md and LICENSE to project root ---")
    
    try:
        print(f"Attempting to copy '{os.path.abspath(README_SOURCE_RELATIVE)}' to '{os.path.abspath(README_DEST)}'")
        shutil.copy2(os.path.abspath(README_SOURCE_RELATIVE), README_DEST)
        print(f"Attempting to copy '{os.path.abspath(LICENSE_SOURCE_RELATIVE)}' to '{os.path.abspath(LICENSE_DEST)}'")
        shutil.copy2(os.path.abspath(LICENSE_SOURCE_RELATIVE), LICENSE_DEST)
        print("SUCCESS: README.md and LICENSE copied successfully for build process.")
    except FileNotFoundError as e:
        print(f"ERROR: Source file not found: {e}")
        print("Please ensure your 'README_SOURCE_RELATIVE' and 'LICENSE_SOURCE_RELATIVE' paths are correct.")
        sys.exit(1) # Exit on critical error
    except Exception as e:
        print(f"ERROR: Failed to copy files: {e}")
        sys.exit(1) # Exit on critical error

    try:
        # --- Build the package ---
        print("\n--- Step 2: Building Python package (creating sdist and wheel) ---")
        run_command(f"{sys.executable} -m build", "Running build command")

        # --- Upload to PyPI (or TestPyPI) ---
        print("\n--- Step 3: Uploading package to PyPI ---")
        # To upload to TestPyPI for testing, uncomment the line below and comment out the PyPI line:
        # print("Note: Uploading to TestPyPI. Use '--repository pypi' for actual PyPI.")
        # run_command(f"{sys.executable} -m twine upload --repository testpypi dist/*", "Running Twine upload to TestPyPI")
        
        print("Note: Uploading to official PyPI.")
        run_command(f"{sys.executable} -m twine upload dist/*", "Running Twine upload to PyPI")

    except Exception as e:
        print(f"\n!!! Publishing process failed due to an error: {e} !!!")
    finally:
        # --- Post-upload steps ---
        print("\n--- Step 4: Cleaning up copied README.md and LICENSE ---")
        if os.path.exists(README_DEST):
            print(f"Removing temporary file: {os.path.abspath(README_DEST)}")
            os.remove(README_DEST)
        else:
            print(f"Temporary README.md not found at {os.path.abspath(README_DEST)}, nothing to remove.")
        
        if os.path.exists(LICENSE_DEST):
            print(f"Removing temporary file: {os.path.abspath(LICENSE_DEST)}")
            os.remove(LICENSE_DEST)
        else:
            print(f"Temporary LICENSE not found at {os.path.abspath(LICENSE_DEST)}, nothing to remove.")
        print("Cleanup complete.")

    print("\n--- PyPI Publishing Process Finished ---")

if __name__ == "__main__":
    main()