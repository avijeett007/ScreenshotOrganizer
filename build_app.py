import os
import sys
import platform
import subprocess
import shutil

def create_icon():
    """Create platform-specific icons"""
    # Ensure the create_icon.py script exists and run it
    if os.path.exists('create_icon.py'):
        subprocess.run([sys.executable, 'create_icon.py'])

def install_requirements():
    """Install required packages"""
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

def build_executable():
    """Build the executable for the current platform"""
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')

    # Build using PyInstaller
    subprocess.run(['pyinstaller', 'screenshot_organizer.spec'])

    # Create distribution directory
    dist_dir = 'dist_package'
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)

    # Copy necessary files
    if platform.system() == 'Darwin':  # macOS
        shutil.copytree('dist/ScreenshotOrganizer.app', f'{dist_dir}/ScreenshotOrganizer.app')
        # Create DMG (optional)
        try:
            subprocess.run(['hdiutil', 'create', '-volname', 'ScreenshotOrganizer', 
                          '-srcfolder', f'{dist_dir}/ScreenshotOrganizer.app', 
                          '-ov', '-format', 'UDZO', 
                          f'{dist_dir}/ScreenshotOrganizer.dmg'])
        except Exception as e:
            print(f"Could not create DMG: {e}")
    
    elif platform.system() == 'Windows':  # Windows
        shutil.copytree('dist/ScreenshotOrganizer', f'{dist_dir}/ScreenshotOrganizer')
        # Create ZIP archive
        shutil.make_archive(f'{dist_dir}/ScreenshotOrganizer-Windows', 'zip', f'{dist_dir}/ScreenshotOrganizer')

def main():
    print("Installing requirements...")
    install_requirements()

    print("Creating icons...")
    create_icon()

    print("Building executable...")
    build_executable()

    print("Build complete! Check the dist_package directory for the executable.")

if __name__ == "__main__":
    main()
