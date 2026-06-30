from PIL import Image, ImageChops

def trim(im):
    # Find the background color at the top-left corner
    bg_color = im.getpixel((0, 0))
    bg = Image.new(im.mode, im.size, bg_color)
    
    # Calculate difference between the image and its background color
    diff = ImageChops.difference(im, bg)
    
    # Add tolerance to handle slight gradients or compressed artifacts
    diff = ImageChops.add(diff, diff, 2.0, -100)
    
    # Get the bounding box of non-background content
    bbox = diff.getbbox()
    if bbox:
        # Add a tiny 10px padding on top and bottom for breathing room
        left, top, right, bottom = bbox
        top = max(0, top - 10)
        bottom = min(im.size[1], bottom + 10)
        return im.crop((left, top, right, bottom))
    return im

try:
    print("Opening logo.png...")
    im = Image.open("logo.png")
    print(f"Original size: {im.size}")
    
    cropped_im = trim(im)
    cropped_im.save("logo_cropped.png")
    print(f"Cropped size: {cropped_im.size}")
    print("Cropped logo saved as logo_cropped.png successfully!")
except Exception as e:
    print(f"Error cropping image: {str(e)}")
