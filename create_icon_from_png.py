#!/usr/bin/env python3
"""
Create app icons from existing PNG file
"""
import os
from PIL import Image
import sys

def create_icons_from_png():
    """Create icons from existing app_logo_1024.png"""
    
    # Check if source file exists
    source_file = "app_logo_1024.png"
    if not os.path.exists(source_file):
        print(f"❌ Source file {source_file} not found!")
        return
    
    print(f"🎨 Creating icons from {source_file}...")
    
    # Open the source image
    try:
        source_img = Image.open(source_file)
        print(f"✅ Loaded source image: {source_img.size}")
    except Exception as e:
        print(f"❌ Error loading source image: {e}")
        return
    
    # Create macOS .icns
    create_icns(source_img)
    
    # Create Windows .ico
    create_ico(source_img)
    
    print("\n🎉 All icons created from your PNG!")

def create_icns(source_img):
    """Create macOS .icns file from source image"""
    print("🍎 Creating macOS .icns...")
    
    # Create iconset directory
    iconset_dir = "app.iconset"
    os.makedirs(iconset_dir, exist_ok=True)
    
    # Sizes needed for .icns
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    
    for size in sizes:
        # Resize image
        resized_img = source_img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save regular size
        resized_img.save(f"{iconset_dir}/icon_{size}x{size}.png", 'PNG')
        print(f"  ✅ icon_{size}x{size}.png")
        
        # Save 2x size for sizes <= 512
        if size <= 512:
            double_size = size * 2
            double_img = source_img.resize((double_size, double_size), Image.Resampling.LANCZOS)
            double_img.save(f"{iconset_dir}/icon_{size}x{size}@2x.png", 'PNG')
            print(f"  ✅ icon_{size}x{size}@2x.png")
    
    # Create .icns using iconutil (macOS only)
    if sys.platform == "darwin":
        os.system("iconutil -c icns app.iconset")
        print("✅ Created app.icns")
    else:
        print("⚠️ .icns creation requires macOS")

def create_ico(source_img):
    """Create Windows .ico file from source image"""
    print("🪟 Creating Windows .ico...")
    
    # Sizes needed for .ico
    sizes = [16, 32, 64, 128, 256]
    
    images = []
    for size in sizes:
        resized_img = source_img.resize((size, size), Image.Resampling.LANCZOS)
        images.append(resized_img)
    
    # Create .ico file
    images[0].save("icon.ico", format='ICO', sizes=[(size, size) for size in sizes])
    print("✅ Created icon.ico")

if __name__ == "__main__":
    create_icons_from_png()
