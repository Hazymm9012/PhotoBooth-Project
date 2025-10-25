from PIL import Image, ImageTk
from io import BytesIO
from flask import session, current_app, url_for
from datetime import datetime, timedelta, UTC
from models import Photo, db, PhotoType, PhotoStatus
from PIL import Image, ImageDraw, ImageFont

import pymysql
import secrets
import string
import jwt
import os
import time
import base64 
import requests
import socket
import hmac 
import hashlib
import re 


from sqlalchemy.engine.url import make_url, URL


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
        if b64_string.startswith("data:"):
            b64_string = re.sub(r"^data:[^;]+;base64,", "", b64_string)
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

def create_database_connection(db_url):
    """
    Accepts a mysql+pymysql URL (str or sqlalchemy URL).
    Connects without selecting a DB, then CREATE DATABASE IF NOT EXISTS.
    """
    # Parse if needed
    if isinstance(db_url, str):
        url = make_url(db_url)
    elif isinstance(db_url, URL):
        url = db_url
    else:
        raise TypeError("db_url must be a str or sqlalchemy.engine.url.URL")

    if url.drivername != "mysql+pymysql":
        raise ValueError(f"Unsupported driver: {url.drivername}")

    db_name = url.database
    if not db_name:
        raise ValueError("Database name missing in URL")

    # Handle TCP vs Unix socket
    # If using ?unix_socket=/tmp/mysql.sock in the URL, host may be None
    unix_socket = url.query.get("unix_socket")
    conn_kwargs = dict(
        user=url.username,
        password=url.password,
        charset="utf8mb4",
        autocommit=True,
    )
    if unix_socket:
        conn_kwargs["unix_socket"] = unix_socket
    else:
        conn_kwargs["host"] = url.host or "127.0.0.1"
        conn_kwargs["port"] = url.port or 3306

    # Connect WITHOUT selecting a DB
    conn = pymysql.connect(**conn_kwargs)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
            )
    finally:
        conn.close()
        
# Generate secure link for the image file
def get_secure_image_url(filename, add_expiration=True, download=False):
    """Generate a secure link for the image file using JWT token.

    Args:
        filename (str): The name of the image file.

    Returns:
        str: A secure link to access the image file.
    """
    payload = {
        "image_filename": f"{filename}"
    }
    
    if add_expiration:
        # Set expiration time for the token (10 minutes)
        payload['exp'] = datetime.now(UTC) + timedelta(minutes=10)
    
    # Generate token
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm='HS256')
    token = token if isinstance(token, str) else token.decode("utf-8")
    
    # Create a secure link
    secure_link = url_for('photo.view_secure_image', token=token, download=download, _external=True)
    return secure_link

def save_image_to_db(path, image_data, timestamp, method):
    """Save the image to the database."""
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "wb") as file:
        file.write(image_data)
    print(f"{method.capitalize()} Photo captured and saved as {path}")

    unique_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    photo_frame = session.get('photo_size')
    photo = Photo(path="/" + path, filename=f"photo_{timestamp}.png", unique_code=unique_code, type=PhotoType.AI if method == "ai" else PhotoType.ORIGINAL,
                  frame="7 cm x 10 cm" if photo_frame == "frame1" else "14 cm x 10 cm",
                  date_of_save=datetime.now(UTC) + timedelta(hours=8))
    db.session.add(photo)
    db.session.commit()

def save_preview_image(path, image_data):
    """Save the preview image with a watermark."""
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "wb") as file:
        file.write(image_data)
    print(f"Preview Photo captured and saved as {path}")

    preview_image = Image.open(path)
    draw = ImageDraw.Draw(preview_image)
    draw.text((10, 10), "PREVIEW ONLY", fill=(255, 255, 255), font=ImageFont.load_default(45))
    preview_image.save(path, "JPEG")