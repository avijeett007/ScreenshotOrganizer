from PIL import Image, ImageDraw

# Create a new image with a white background
size = (128, 128)
icon = Image.new('RGB', size, 'white')
draw = ImageDraw.Draw(icon)

# Draw a simple camera icon
draw.rectangle([20, 30, 108, 98], outline='black', width=4)
draw.rectangle([50, 20, 78, 30], fill='black')
draw.ellipse([44, 44, 84, 84], outline='black', width=4)

# Save the icon
icon.save('icon.png')
