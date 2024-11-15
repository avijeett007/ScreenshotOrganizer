import os
import platform
from PIL import Image, ImageDraw

def create_base_icon():
    """Create the base icon as PNG"""
    # Create a new image with a white background
    size = (1024, 1024)  # Larger size for better quality
    icon = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(icon)

    # Calculate proportions based on new size
    scale = size[0] / 128
    
    # Draw a simple camera icon, scaled up
    draw.rectangle([20*scale, 30*scale, 108*scale, 98*scale], outline='black', width=int(4*scale))
    draw.rectangle([50*scale, 20*scale, 78*scale, 30*scale], fill='black')
    draw.ellipse([44*scale, 44*scale, 84*scale, 84*scale], outline='black', width=int(4*scale))

    # Save the high-res PNG
    icon.save('icon.png')
    return icon

def create_icns(icon):
    """Create macOS .icns file"""
    if platform.system() != 'Darwin':
        print("Skipping .icns creation on non-macOS platform")
        return
    
    try:
        import subprocess
        # Save icon in required sizes
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        iconset_dir = 'icon.iconset'
        os.makedirs(iconset_dir, exist_ok=True)
        
        for size in sizes:
            # Normal resolution
            icon_size = size, size
            resized = icon.resize(icon_size, Image.Resampling.LANCZOS)
            resized.save(f'{iconset_dir}/icon_{size}x{size}.png')
            
            # High resolution (2x)
            if size <= 512:
                icon_size = size * 2, size * 2
                resized = icon.resize(icon_size, Image.Resampling.LANCZOS)
                resized.save(f'{iconset_dir}/icon_{size}x{size}@2x.png')
        
        # Convert to icns using iconutil
        subprocess.run(['iconutil', '-c', 'icns', iconset_dir])
        
        # Clean up iconset directory
        import shutil
        shutil.rmtree(iconset_dir)
        
    except Exception as e:
        print(f"Error creating .icns file: {e}")

def create_ico(icon):
    """Create Windows .ico file"""
    try:
        # Windows icon sizes
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        icon.save('icon.ico', format='ICO', sizes=sizes)
    except Exception as e:
        print(f"Error creating .ico file: {e}")

def main():
    # Create base icon
    icon = create_base_icon()
    
    # Create platform-specific icons
    create_icns(icon)
    create_ico(icon)

if __name__ == '__main__':
    main()
