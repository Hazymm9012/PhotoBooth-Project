from PIL import Image, ImageTk
from io import BytesIO
from flask import session

import os
import time
import base64 
import requests
import socket
import hmac 
import hashlib


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
    pil_image.save(buffer, format="png")
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

def encode_image(file_path):
    with open(file_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")
    return base64_image

def is_valid_base64(b64_string):
    try:
        base64.b64decode(b64_string, validate=True)
        return True
    except Exception:
        return False
    
def encode_image_to_data_url(base64_str, format="PNG"):
    if base64_str.startswith("data:image"):
        base64_str = base64_str.split(",", 1)[1]
    image_data = base64.b64decode(base64_str)
    image_encoded = Image.open(BytesIO(image_data))
    buffered = BytesIO()
    image_encoded.save(buffered, format=format)
    encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return encoded   

def get_local_ip():
    """"Get the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def verify_hitpay_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Validate HitPay webhook signature. (HMAC-SHA256) of raw JSON payload"""
    computed_hmac = hmac.new(
        key=secret.encode('utf-8'),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Avoid timing attacks
    return hmac.compare_digest(computed_hmac, signature)

def clear_session():
    """Clear the session data."""
    camera_data = session.get('camera_data')
    session_keys = list(session.keys())
    
    for key in session_keys:
        if key != 'camera_session':
            session.pop(key)

    
    

