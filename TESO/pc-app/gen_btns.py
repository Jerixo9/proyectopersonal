from PIL import Image, ImageDraw, ImageFont
import os

def create_gradient_button(filename, text, size=(720, 80)):
    w, h = size
    # Create base image
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw gradient (from #9bc5f5 to #d4a7f2) or something similar
    color1 = (175, 226, 255) # cyan-ish
    color2 = (226, 175, 255) # purple-ish
    
    color1 = (110, 200, 255)
    color2 = (220, 150, 255)
    
    # Generate gradient background
    for x in range(w):
        r = int(color1[0] + (color2[0] - color1[0]) * x / w)
        g = int(color1[1] + (color2[1] - color1[1]) * x / w)
        b = int(color1[2] + (color2[2] - color1[2]) * x / w)
        draw.line([(x, 0), (x, h)], fill=(r, g, b, 255))
        
    # Apply rounded corners using a mask
    mask = Image.new('L', (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = h // 2
    mask_draw.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    img.putalpha(mask)
    
    # Draw text
    try:
        font = ImageFont.truetype("arialbd.ttf", 32)
    except:
        font = ImageFont.load_default()
        
    # Get text bbox
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    tw = right - left
    th = bottom - top
    
    tx = (w - tw) / 2
    # Adjust vertical centering
    ty = (h - th) / 2 - top
    
    draw.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)
    
    out_path = os.path.join(os.path.dirname(__file__), "assets", filename)
    img.save(out_path)
    print(f"Saved {out_path}")

create_gradient_button("btn_primary_prep.png", "Enviar a Cocina", size=(320, 64))
create_gradient_button("btn_primary_send.png", "Marcar Enviado", size=(320, 64))
