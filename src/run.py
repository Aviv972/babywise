import os
import sys
import subprocess
import venv
from pathlib import Path

def create_venv():
    """Create a virtual environment if it doesn't exist"""
    venv_path = Path("venv")
    if not venv_path.exists():
        print("Creating virtual environment...")
        venv.create(venv_path, with_pip=True)
        return True
    return False

def install_requirements():
    """Install requirements in the virtual environment"""
    print("Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def run_server():
    """Run the FastAPI server"""
    print("Starting server...")
    subprocess.check_call([sys.executable, "src/server.py"])

def main():
    # Get the virtual environment activation script path
    if sys.platform == "win32":
        activate_script = "venv\\Scripts\\activate.bat"
    else:
        activate_script = "venv/bin/activate"

    # Create venv if it doesn't exist
    if create_venv():
        # Activate the virtual environment
        activate_command = f"source {activate_script}" if sys.platform != "win32" else activate_script
        os.system(activate_command)
        
        # Install requirements
        install_requirements()

    # Run the server
    run_server()

if __name__ == "__main__":
    main() 