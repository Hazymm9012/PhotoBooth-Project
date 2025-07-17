from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from together import Together
from tkinter import *
from PIL import Image, ImageTk
from io import BytesIO
from utils import read_image_from_base64, read_image_from_folder, pil_to_base64, stitch_images

import os
import time
import base64 
import requests

# Ensure the Together API key is set in the environment variables
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_insecure_key')
client = Together(api_key=os.environ.get('TOGETHER_API_KEY'))
PHOTO_DIR = 'static/photos'

# Home Page
@app.route('/')
def index():
    photos = os.listdir(PHOTO_DIR)
    return render_template('index.html', photos=photos)

# Preview page
@app.route('/preview')
def preview():
    photo_width = session.get('image_width')
    photo_height = session.get('image_height')
    print(f"Retrieved values: width {photo_width}, height {photo_height}")
    return render_template('preview.html', photo_width=photo_width, photo_height=photo_height)

# Choose print size for photo
@app.route('/choose_size')
def choose_size():
    return render_template('chooseSize.html')

# Set print size of the photo
@app.route('/set_size', methods=['POST'])
def set_size():
    image_width = 0
    image_height = 0
    selected_size = request.form.get('size')
    session['photo_size'] = selected_size
    if selected_size == "frame1":
        image_width = 832
        image_height = 1184
    elif selected_size == "frame2":
        image_width = 1664
        image_height = 1184
    session['image_width'] = image_width
    session['image_height'] = image_height
    print(f"Selected frame: {selected_size}")
    print(f"Selected weight & height: {image_width} px & {image_height} px")
    return redirect(url_for('preview'))

# Upload and generate pixar-style photo
@app.route('/upload', methods=['POST'])
def upload():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            print("❌ No image data provided.")
            return "No image data provided", 400
        
        background_image_data = read_image_from_folder(data.get("background_filename"))
        decoded_image_data = read_image_from_base64(data.get("image"))
        processed_image = stitch_images(decoded_image_data, background_image_data)
        base64_image = pil_to_base64(processed_image)
        
        # Retrieve current session requested photo width and height
        photo_width = session.get('image_width')
        photo_height = session.get('image_height')
        
        response = client.images.generate(
            model = "black-forest-labs/FLUX.1-kontext-dev",
            width = photo_width,
            height = photo_height,
            prompt = "Change this image into a pixar-style image. Change all the background into pixar-style at the disney castle",
            image_url = data.get("image"),
        )
        
        #if not response or not response.get('image_url'):
        #    raise Exception("Failed to generate image.")
        print("Image has been successfully generated.")
        print(response.data[0].url)
        return jsonify({"image_url": response.data[0].url}), 200
    
    except requests.exceptions.RequestException as re:
        print(f"❌ Network error: {re}")
        
    except Exception as e:
        print(f"❌ API Error: {e}")
    
    return None    
    
# Capture Photo 
@app.route('/save_image', methods=['POST'])
def save_image():
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'No Image Provided'}, 400)
        
        try:
            header, base64_image = image_data.split(',', 1)
        except ValueError:
            return jsonify({'error': 'Invalid base64 image format'}), 400
        
        if not os.path.exists(PHOTO_DIR):
            os.makedirs(PHOTO_DIR)
        
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{PHOTO_DIR}/photo_{timestamp}.jpg"
        
        with open (filename, "wb") as file:
            file.write(base64.b64decode(base64_image))
        
        print(f"Photo captured and saved as {filename}")
        return jsonify({"filename": filename}), 200
    
    except Exception as e:
        print(f"❌ Error saving photo: {e}")
        return jsonify({"error": str(e)}), 500
        

# Display Photo
@app.route("/photo/<filename>")
def show_photo(filename):
    return render_template('photo.html', filename=filename)


if __name__ == '__main__':
    app.run(debug=True)

