#!/usr/bin/env python3
"""
Create app icons for Video Splitter
"""
import os
from PIL import Image, ImageDraw, ImageFont
import sys

def create_icon(size, filename):
    """Create icon with video splitter theme"""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colors
    bg_color = (41, 98, 255)  # Blue background
    film_color = (255, 255, 255)  # White film strips
    scissor_color = (255, 69, 0)  # Orange scissors
    
    # Draw rounded rectangle background
    margin = size // 10
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 8,
        fill=bg_color
    )
    
    # Draw film strip on left
    film_width = size // 6
    film_height = size // 8
    film_spacing = size // 16
    
    for i in range(3):
        y = margin + size // 4 + i * (film_height + film_spacing)
        draw.rectangle([margin + 5, y, margin + 5 + film_width, y + film_height], fill=film_color)
        # Film holes
        hole_size = size // 40
        for j in range(3):
            hole_x = margin + 5 + film_width // 4 + j * (film_width // 4)
            draw.ellipse([hole_x - hole_size//2, y + film_height//2 - hole_size//2,
                         hole_x + hole_size//2, y + film_height//2 + hole_size//2], fill=bg_color)
    
    # Draw film strip on right
    for i in range(3):
        y = margin + size // 4 + i * (film_height + film_spacing)
        draw.rectangle([size - margin - 5 - film_width, y, size - margin - 5, y + film_height], fill=film_color)
        # Film holes
        hole_size = size // 40
        for j in range(3):
            hole_x = size - margin - 5 - film_width + film_width // 4 + j * (film_width // 4)
            draw.ellipse([hole_x - hole_size//2, y + film_height//2 - hole_size//2,
                         hole_x + hole_size//2, y + film_height//2 + hole_size//2], fill=bg_color)
    
    # Draw scissors in center
    center_x = size // 2
    center_y = size // 2
    scissor_size = size // 3
    
    # Scissor blades (X shape)
    blade_width = size // 25
    blade_length = scissor_size // 2
    
    # Left blade
    draw.polygon([
        (center_x - blade_length//2, center_y - blade_length//2),
        (center_x + blade_length//2, center_y + blade_length//2),
        (center_x + blade_length//2 - blade_width, center_y + blade_length//2),
        (center_x - blade_length//2 + blade_width, center_y - blade_length//2)
    ], fill=scissor_color)
    
    # Right blade
    draw.polygon([
        (center_x - blade_length//2, center_y + blade_length//2),
        (center_x + blade_length//2, center_y - blade_length//2),
        (center_x + blade_length//2 - blade_width, center_y - blade_length//2),
        (center_x - blade_length//2 + blade_width, center_y + blade_length//2)
    ], fill=scissor_color)
    
    # Center pivot
    pivot_size = size // 20
    draw.ellipse([center_x - pivot_size, center_y - pivot_size,
                 center_x + pivot_size, center_y + pivot_size], fill=film_color)
    
    # Save icon
    img.save(filename, 'PNG')
    print(f"✅ Created {filename} ({size}x{size})")

def create_icns():
    """Create macOS .icns file"""
    # Create different sizes for .icns
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    
    # Create iconset directory
    iconset_dir = "app.iconset"
    os.makedirs(iconset_dir, exist_ok=True)
    
    for size in sizes:
        # Create regular size
        create_icon(size, f"{iconset_dir}/icon_{size}x{size}.png")
        # Create 2x size
        if size <= 512:
            create_icon(size * 2, f"{iconset_dir}/icon_{size}x{size}@2x.png")
    
    # Create .icns using iconutil (macOS only)
    if sys.platform == "darwin":
        os.system("iconutil -c icns app.iconset")
        print("✅ Created app.icns")
    else:
        print("⚠️ .icns creation requires macOS")

def create_ico():
    """Create Windows .ico file"""
    # Create sizes needed for .ico
    sizes = [16, 32, 64, 128, 256]
    
    images = []
    for size in sizes:
        create_icon(size, f"icon_{size}x{size}.png")
        img = Image.open(f"icon_{size}x{size}.png")
        images.append(img)
    
    # Create .ico file
    images[0].save("icon.ico", format='ICO', sizes=[(size, size) for size in sizes])
    print("✅ Created icon.ico")
    
    # Clean up temporary files
    for size in sizes:
        os.remove(f"icon_{size}x{size}.png")

def create_app_logo():
    """Create large app logo for marketing"""
    create_icon(1024, "app_logo_1024.png")
    print("✅ Created app_logo_1024.png")

if __name__ == "__main__":
    print("🎨 Creating Video Splitter icons...")
    
    # Create macOS icon
    create_icns()
    
    # Create Windows icon
    create_ico()
    
    # Create app logo
    create_app_logo()
    
    print("\n🎉 All icons created successfully!")
    print("📁 Files created:")
    print("   - app.icns (macOS)")
    print("   - icon.ico (Windows)")
    print("   - app_logo_1024.png (marketing)")
