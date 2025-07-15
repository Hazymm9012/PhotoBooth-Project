from flask import Flask, render_template, request, redirect, url_for
import cv2 
from tkinter import *
from PIL import Image, ImageTk
import os
import time 

app = Flask(__name__)
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

# Capture Photo 
@app.route('/capture', methods=['POST'])
def capture():
    if not os.path.exists(PHOTO_DIR):
        os.makedirs(PHOTO_DIR)
    
    video = cv2.VideoCapture(0)
    for _ in range(10):
        ret, frame = video.read()
        
    ret, frame = video.read()
    
    if ret:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{PHOTO_DIR}/photo_{timestamp}.png"
        cv2.imwrite(filename, frame)
        print(f"Photo saved as {filename}")
    
    video.release()
    return redirect(url_for('index'))

# Display Photo
@app.route("/photo/<filename>")
def show_photo(filename):
    return render_template('photo.html', filename=filename)

if __name__ == '__main__':
    app.run(debug=True)

