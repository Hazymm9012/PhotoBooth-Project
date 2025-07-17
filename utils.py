from PIL import Image, ImageTk
from io import BytesIO

import os
import time
import base64 
import requests

# Load image from file and convert to data URI
def load_image_as_data_uri(image_path):
    try:
        with open(image_path, "rb") as file:
            encoded = base64.b64encode(file.read()).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
    except FileNotFoundError:
        raise Exception("Image file not found.")
    except Exception as e:
        raise Exception(f"Failed to read/encode image: {e}")
    

def pil_to_base64(pil_image):
    buffer = BytesIO()
    pil_image.save(buffer, format="JPEG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return "data:image/jpeg;base64," + img_str

def read_image_from_folder(file_name):
    try:
        image_path = os.path.join("static/images/", file_name)
        image = Image.open(image_path)
        return image
    except FileNotFoundError:
        print(f"File not found: {file_name}")
        return None
    except Exception as e:
        print(f"Error reading image: {e}")
        return None

def read_image_from_base64(json_img_str):
    if json_img_str.startswith("data:image"):
        json_img_str = json_img_str.split(",", 1)[1]  # remove data URL prefix
    image_data = base64.b64decode(json_img_str)
    return Image.open(BytesIO(image_data))
    
def resize_to_match_height(img1, img2):
    """
    Resize both images to the same height (min of the two).
    """
    print("Type of img_a:", type(img1))
    print("Type of img_b:", type(img2))
    h = min(img1.height, img2.height)
    def resize(img):
        w = int(img.width * h / img.height)
        return img.resize((w, h))
    return resize(img1), resize(img2)

def stitch_images(image_a, image_b, spacing=10, bg_color=(255, 255, 255)):
    """
    Stitch two PIL images horizontally with spacing.
    """
    img1, img2 = resize_to_match_height(image_a, image_b)

    total_width = img1.width + img2.width + spacing
    height = img1.height

    composite = Image.new("RGB", (total_width, height), bg_color)
    composite.paste(img1, (0, 0))
    composite.paste(img2, (img1.width + spacing, 0))

    return composite