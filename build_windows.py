#!/usr/bin/env python3
"""
Build script for Windows version of Video Splitter
"""
import os
import sys
import subprocess
import shutil

def create_windows_build():
    """Create Windows executable"""
    print("🔧 Creating Windows build...")
    
    # Install PyInstaller if not already installed
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Build the executable
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",           # Create directory with executable
        "--windowed",         # No console window
        "--name", "VideoSplitter",
        "--icon", "icon.ico",  # Use your custom icon
        "--add-binary", "ffmpeg.exe;.",  # Include FFmpeg
        "--add-binary", "ffprobe.exe;.", # Include FFprobe
        "main_windows.py"     # Use Windows-specific version
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Windows build created successfully!")
        print("📁 Executable location: dist/VideoSplitter/VideoSplitter.exe")
        
        # Create README for Windows
        create_windows_readme()
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False
    
    return True

def create_windows_readme():
    """Create Windows-specific README"""
    readme_content = """# Video Splitter - Windows Version

## 📦 Installation

1. Download the latest release from GitHub
2. Extract the ZIP file
3. Run `VideoSplitter.exe`

## ⚙️ Requirements

- Windows 10 or later
- FFmpeg (included in the package)

## 🚀 Usage

1. **Select video file**: Drag & drop or click "Browse"
2. **Set duration**: Choose segment length in seconds
3. **Choose resolution**: Select aspect ratio (optional)
4. **Pick scaling**: Full frame (crop) or fit with bars
5. **Select mode**: Fast (no re-encoding) or Precise (re-encoding)
6. **Click START**: Begin processing

## 📁 Output

Files are saved in a folder named after your video file in the same directory.

## 🔧 Troubleshooting

**FFmpeg not found**: The program includes FFmpeg, but if you have issues:
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract to the same folder as VideoSplitter.exe

**Antivirus warning**: Some antivirus software may flag the executable. This is a false positive - add to exceptions.

## 📞 Support

For issues and feature requests, please visit the GitHub repository.
"""
    
    with open("dist/VideoSplitter/README_Windows.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("📝 Windows README created")

def create_installer_script():
    """Create NSIS installer script"""
    nsis_script = """
; Video Splitter Installer Script
!define APPNAME "Video Splitter"
!define VERSION "1.0"
!define PUBLISHER "Video Splitter Team"
!define DESCRIPTION "Video Splitter - Split videos into segments"
!define URL "https://github.com/your-repo/video-splitter"

; Include Modern UI
!include "MUI2.nsh"

; General
Name "${APPNAME}"
OutFile "${APPNAME}_Setup_${VERSION}.exe"
InstallDir "$PROGRAMFILES\\${APPNAME}"
InstallDirRegKey HKLM "Software\\${APPNAME}" "InstallPath"
RequestExecutionLevel admin

; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "icon.ico"
!define MUI_UNICON "icon.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer Sections
Section "Main Program" SecMain
    SetOutPath "$INSTDIR"
    File /r "dist\\VideoSplitter\\*"
    
    ; Create Start Menu shortcut
    CreateShortCut "$SMPROGRAMS\\${APPNAME}.lnk" "$INSTDIR\\VideoSplitter.exe"
    
    ; Create Desktop shortcut
    CreateShortCut "$DESKTOP\\${APPNAME}.lnk" "$INSTDIR\\VideoSplitter.exe"
    
    ; Registry entries for uninstall
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "DisplayName" "${APPNAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "UninstallString" "$INSTDIR\\Uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "Publisher" "${PUBLISHER}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "URLInfoAbout" "${URL}"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\\Uninstall.exe"
SectionEnd

; Uninstaller Section
Section "Uninstall"
    Delete "$INSTDIR\\Uninstall.exe"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\\${APPNAME}.lnk"
    Delete "$DESKTOP\\${APPNAME}.lnk"
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}"
SectionEnd
"""
    
    with open("installer.nsi", "w", encoding="utf-8") as f:
        f.write(nsis_script)
    
    print("📝 NSIS installer script created")

if __name__ == "__main__":
    print("🚀 Building Video Splitter for Windows...")
    
    # Check if we're on Windows
    if sys.platform != "win32":
        print("⚠️ This script should be run on Windows")
        print("💡 Cross-platform compilation is complex, consider using GitHub Actions")
        sys.exit(1)
    
    # Create the build
    if create_windows_build():
        create_installer_script()
        print("\n✅ Windows build complete!")
        print("📦 Next steps:")
        print("1. Test the executable in dist/VideoSplitter/")
        print("2. Use NSIS to create installer from installer.nsi")
        print("3. Upload to GitHub Releases")
    else:
        print("❌ Build failed!")
        sys.exit(1)
