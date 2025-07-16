from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from together import Together
from tkinter import *
from PIL import Image, ImageTk

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
    return render_template('preview.html')

# Choose print size for photo
@app.route('/choose_size')
def choose_size():
    return render_template('chooseSize.html')

# Set print size of the photo
@app.route('/set_size', methods=['POST'])
def set_size():
    selected_size = request.form.get('size')
    session['photo_size'] = selected_size
    print(f"Selected frame: {selected_size}")
    return redirect(url_for('preview'))

# Upload and generate pixar-style photo
@app.route('/upload', methods=['POST'])
def upload():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            print("❌ No image data provided.")
            return "No image data provided", 400
        
        image_data = data['image']
        
        # image_data_uri = load_image_as_data_uri(image_data)
        
        response = client.images.generate(
            model = "black-forest-labs/FLUX.1-kontext-dev",
            width = 1024,
            height = 768,
            prompt = "A Pixar-style 3D animated [man/woman/child] with [specific traits], large shiny eyes, cute facial proportions, soft lighting, digital painting in Pixar style.",
            image_url = image_data,
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
        if 'image' not in data:
            return "No image data provided", 400
        
        header, base64_image = data['image'].split(',', 1)
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

if __name__ == '__main__':
    app.run(debug=True)

