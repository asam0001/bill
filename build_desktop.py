"""
MediTrack ERP - Desktop Standalone Binary Packaging Script
Builds a self-contained, offline Windows .exe executable using PyInstaller.
Also packages a standalone zip archive for easy sharing via USB, Git releases, or Drive.

Usage:
    python build_desktop.py
Output:
    dist/MediTrack/MediTrack.exe
    dist/MediTrack-v2.0-Windows-Portable.zip
"""

import os
import sys
import subprocess
import shutil
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def build_executable():
    print("=" * 60)
    print("MediTrack ERP — Desktop Standalone Executable Builder")
    print("=" * 60)

    # 1. Check for PyInstaller
    try:
        import PyInstaller
        print(f"[1/5] Detected PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("[INFO] PyInstaller not detected. Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Check and generate assets if needed
    icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
    if not os.path.exists(icon_path):
        print("[INFO] Generating application icons...")
        subprocess.check_call([sys.executable, os.path.join(BASE_DIR, "generate_assets.py")])

    # 3. Locate customtkinter asset directory
    try:
        import customtkinter
        ctk_path = os.path.dirname(customtkinter.__file__)
    except ImportError:
        ctk_path = ""

    # 4. Assemble PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=MediTrack",
        "--noconfirm",
        "--onedir",
        "--windowed", # Suppress black terminal window in production
        "--add-data", f"{os.path.join(BASE_DIR, 'mobile')};mobile",
        "--add-data", f"{os.path.join(BASE_DIR, 'assets')};assets",
    ]

    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])

    if ctk_path and os.path.exists(ctk_path):
        cmd.extend(["--add-data", f"{ctk_path};customtkinter"])

    # Hidden imports
    hidden_imports = [
        "reportlab",
        "customtkinter",
        "qrcode",
        "PIL",
        "openpyxl",
        "sqlite3",
        "decimal",
        "json",
        "http.server",
        "socket",
        "threading",
        "urllib.parse"
    ]
    for hi in hidden_imports:
        cmd.extend(["--hidden-import", hi])

    cmd.append(os.path.join(BASE_DIR, "main.py"))

    print("\n[2/5] Executing PyInstaller build pipeline...")
    subprocess.check_call(cmd, cwd=BASE_DIR)

    output_dir = os.path.join(BASE_DIR, "dist", "MediTrack")
    print("\n[3/5] Standalone executable directory created at:")
    print("     ", output_dir)

    # Copy launcher helper into dist/MediTrack
    launcher_bat = os.path.join(output_dir, "Launch MediTrack.bat")
    with open(launcher_bat, "w") as f:
        f.write("@echo off\r\nstart \"\" \"MediTrack.exe\"\r\n")

    # 5. Create Portable Release Zip Archive
    print("\n[4/5] Packaging Portable ZIP Archive for distribution...")
    zip_filename = os.path.join(BASE_DIR, "dist", "MediTrack-v2.0-Windows-Portable.zip")
    if os.path.exists(zip_filename):
        os.remove(zip_filename)

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, os.path.join(BASE_DIR, "dist"))
                zipf.write(abs_path, rel_path)

    zip_size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
    print(f"      Portable ZIP generated: {zip_filename} ({zip_size_mb:.1f} MB)")

    print("\n[5/5] SUCCESS! MediTrack standalone desktop application is ready for distribution.")
    print("      Share the ZIP file with any PC user. No Python installation required.")
    print("=" * 60)


if __name__ == "__main__":
    build_executable()
