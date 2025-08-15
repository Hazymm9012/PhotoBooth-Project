import string
import uuid
from flask import Flask, abort, render_template, request, redirect, url_for, session, jsonify, send_file, flash
from together import Together
from tkinter import *
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from utils import  encode_image, is_valid_base64, encode_image_to_data_url, get_local_ip, verify_hitpay_signature, clear_session, create_database_connection
from payment_status_store import load_status_store, save_status, get_status, get_last_item_from_store
from openai import OpenAI
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db

import os
import time
import base64 
import requests
import qrcode
import jwt
import secrets
import socket

# Load environment variables from .env file
load_dotenv() 

# Initialize Flask app and configure settings
app = Flask(__name__)
migrate = Migrate()
db_url = os.environ.get('DATABASE_URL')

# Check if DATABASE_URL is set in the environment variables
if not db_url:
    raise ValueError("DATABASE_URL environment variable is not set.")

# Create database connection
create_database_connection(db_url)  # Create database connection

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_SECURE"] = True  # Set to True in production
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # Set to 'Strict' in production

# Ensure app, openai, hitpay salt and api keys are set up in .env
app.secret_key = os.environ.get('SECRET_KEY')   
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'), timeout=80)  
HITPAY_SALT = os.environ.get('HITPAY_SALT')
HITPAY_API_KEY = os.environ.get('HITPAY_API_KEY')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')  
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')  

# Set allowed IP addresses for development and production
ALLOWED_IPS = ['202.168.65.122', '127.0.0.1']

# Constants and global variables
PHOTO_DIR = 'full_photos'
PREVIEW_DIR = 'static/preview_photos'

# Initialize the payment status store
payment_status_store = {}

# Load the payment status store from file
load_status_store()

# Initialize SQLAlchemy and Migrate
db.init_app(app)
migrate.init_app(app, db)
from models import Photo, Payment, PhotoStatus  # This needs to be declared after db.init_app(app) to avoid circular imports

# Create database tables if they do not exist
with app.app_context():
    db.drop_all()  # Drop all tables (for development purposes, remove in production)
    db.create_all() # recreates tables from models
    print("Models mapped:", list(db.metadata.tables.keys()))
    

# Check session ID and create a new one if it doesn't exist
@app.before_request
def ensure_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())  
        session['is_new_session'] = True
        print("New session created with ID:", session['session_id'])
    else:
        session['is_new_session'] = False

# Check if the request is from an allowed IP address.
# During development, use local IP address to the ALLOWED_IPS list.        
@app.before_request
def limit_remote_address():
    """Check if the request is from an allowed IP address."""
    client_ip = request.remote_addr
    if client_ip not in ALLOWED_IPS:
        print(f"Access denied for IP: {client_ip}")
        return render_template('403.html'), 403
        
@app.errorhandler(403)
def forbidden_error(error):
    """Handle 403 Forbidden errors by rendering the 403 error page."""
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors by rendering the 404 error page."""
    return render_template('404.html'), 404

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin login route to authenticate the admin user.

    Returns:
        Response: Rendered HTML template for the admin login page or redirects to admin download page upon successful login.
    """
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = request.form.get("password") or ""
        remember = request.form.get("remember") == "1"

        ok = (u == ADMIN_USERNAME and p == ADMIN_PASSWORD)

        if ok:
            session["is_admin"] = True
            if remember:
                session.permanent = True  # respect PERMANENT_SESSION_LIFETIME
            return redirect(url_for("admin_download"))
        flash("Invalid credentials", "danger")
    return render_template("admin_login.html")

# Admin logout route
@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

# Generate secure link for the image file
def get_secure_image_url(filename, add_expiration=True, download=False):
    """Generate a secure link for the image file using JWT token.

    Args:
        filename (str): The name of the image file.

    Returns:
        str: A secure link to access the image file.
    """
    payload = {
        "image_path": f"{filename}"
    }
    
    if add_expiration:
        # Set expiration time for the token (10 minutes)
        payload['exp'] = datetime.now(UTC) + timedelta(minutes=10)
    
    # Generate token
    token = jwt.encode(payload, app.secret_key, algorithm='HS256')
    token = token if isinstance(token, str) else token.decode("utf-8")
    
    # Create a secure link
    secure_link = url_for('view_secure_image', token=token, download=download, _external=True)
    return secure_link

# View secure image
@app.route('/view-secure-image')
def view_secure_image():
    """View a secure image using a JWT token.

    Returns:
        Response: The image file if the token is valid, otherwise an error message.
    """
    token = request.args.get('token')
    download = request.args.get('download', 'false').lower() == 'true'
    if not token:
        return "Invalid or missing token", 400
    
    try:
        # Decode the token
        payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
        image_path = payload.get('image_path')
        full_path = os.path.join(PHOTO_DIR, image_path)
        
        # Check if the image exists
        if not full_path or not os.path.exists(full_path):
            return "Image not found", 404
        
        # Send the image file
        return send_file(full_path, as_attachment=download)
    
    except jwt.ExpiredSignatureError:
        return "Token has expired", 403
    except jwt.InvalidTokenError:
        return "Invalid token", 403

# Home Page
@app.route('/')
def index():
    """Render the home page."""
    return render_template('index.html', index=True)

# Preview page
@app.route('/preview')
def preview():
    """Render the preview page with the photo width and height.

    Returns:
        str: Rendered HTML template for the preview page.
    """
    
    photo_session = session.get('full_image_filename')
    
    # TEMPORARY SOLUTION (This will cause bug when user goes back to set size page)
    photo_width = session.get('image_width')
    photo_height = session.get('image_height')
    img_ratio = photo_width / photo_height
    
    # If the photo session available, restore the session
    if photo_session:
        print("Session photo data found:", photo_session)
        old_photo_size = session.get('old_photo_size')
        return render_template('preview.html', photo_width=photo_width, photo_height=photo_height, session_id=session['session_id'], img_ratio=img_ratio, photo_session=photo_session, old_photo_size=old_photo_size, index=False)
            
    # Check if the width and height of the preview camera are available
    if photo_height is None or photo_height is None:
        return "Photo width and Photo height are required", 403
    
    print(f"Retrieved values: width {photo_width}, height {photo_height}")
    return render_template('preview.html', photo_width=photo_width, photo_height=photo_height, session_id=session['session_id'], img_ratio=img_ratio, index=False)

# Choose print size for photo
@app.route('/choose_size')
def choose_size():
    """Render the choose size page for the photo.

    Returns:
        str: Rendered HTML template for the choose size page.
    """
    return render_template('chooseSize.html', index=False)

# Set print size of the photo
@app.route('/set_size', methods=['POST'])
def set_size():
    """Set the size of the photo based on user selection.

    Returns:
        Response: Redirects to the preview page after setting the size.
    """
    # Get the selected size from the form
    image_width = 0
    image_height = 0
    selected_size = request.form.get('size')
    
    if 'photo_size' in session and session['photo_size'] != selected_size:
        session['old_photo_size'] = session.get('photo_size')
        
    session['photo_size'] = selected_size
    
    # Set the width and height based on the selected size
    if selected_size == "frame1":
        image_width = 832
        image_height = 1184
    elif selected_size == "frame2":
        image_width = 1664
        image_height = 1184
        
    # Store the selected size in the session    
    session['image_width'] = image_width
    session['image_height'] = image_height
    session['photo_size'] = selected_size
    
    # DEBUG: Print the selected size and dimensions
    print(f"Selected frame: {selected_size}")
    print(f"Selected weight & height: {image_width} px & {image_height} px")
    
    return redirect(url_for('preview'))

@app.route('/upload', methods=['POST'])
def upload():
    """Upload an image and generate a pixar-style photo using the ChatGPT/Together API.
    
    Returns:
        Response: JSON response containing the generated image URL or an error message.
    """
    try:
        # Request data from the client
        data = request.get_json()
        
        # Check if the data contains the image and background filename
        if not data or 'image' not in data:
            print("❌ No image data provided.")
            return "No image data provided", 400
        
        # Encode the image and background image to base64 (Format supported by ChatGPT API)
        encoded_background_image = encode_image(os.path.join("static/images/", data.get("background_filename")))
        encoded_image = encode_image_to_data_url(data.get("image"))
        
        # Retrieve current session requested photo width and height
        photo_size = session.get('photo_size')
        
        # Together API client initialization
        #response = client.images.generate(
        #    model = "black-forest-labs/FLUX.1-kontext-dev",
        #    width = photo_width,
        #    height = photo_height,
        #    prompt = "Change this image into a pixar-style image. Change all the background into pixar-style at the disney castle",
        #    image_url = data.get("image"),
        #)
        
        # Set the prompt text for the image generation
        prompt_text = "Change the style of this image into a 3D pixar-style image. Use the second image as the background image for the first image. Make it look cartoonish."
        
        # Call ChatGPT API to generate the image
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt_text},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{encoded_image}",
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{encoded_background_image}",
                    },
                ],
                }
            ],
            tools=[{
                "type": "image_generation",
                "size": "1024x1536" if photo_size == "frame1" else "1536x1024",
                "quality": "medium",    # medium quality for faster response
                }],
        )
        
        # DEBUG: Print the response from the API
        print("Image has been successfully generated.")
        
        # Extract the image URL
        image_outputs = [output for output in response.output if output.type == "image_generation_call"]
        if image_outputs:
            image_base64 = image_outputs[0].result  

            # Return the JSON response
            image_url = f"data:image/png;base64,{image_base64}"
            return jsonify({"image_url": image_url})
        else:
            return jsonify({"error": "No image generated"}), 400
    except requests.exceptions.Timeout:
        print("❌ Request to OpenAI timed out")
        return jsonify({"error": "The request to OpenAI timeout"}), 503
    
    except requests.exceptions.ConnectionError:
        print(f"❌ Network error")
        return jsonify({"error": "Network Connection Error"}),  503
    
    except socket.timeout:
        print(f"❌ Socket timeout")
        return jsonify({"error": "Socket Timeout"}), 504
    
    except Exception as e:
        print(f"❌ API Error: {e}")
        return jsonify({"error": str(e)}), 500
    
# Save an image file from javascript
@app.route('/save_image_file/<method>', methods=['POST'])
def save_image_file(method):
    """Save an image file from javascript request to the folder.

    Returns:
        Response: JSON response with the filename of the saved image or an error message.
    """
    try:
        method = method.lower()
        if method not in ['preview', 'full']:
            return jsonify({'error': 'Invalid method specified'}), 400
        
        # Retrieve the image data from the request
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'No Image Provided'}), 400
        
        try:
            header, base64_image = image_data.split(',', 1)
        except ValueError:
            return jsonify({'error': 'Invalid base64 image format'}), 400
        image_data = base64.b64decode(base64_image)
        timestamp = time.strftime("%d%m%Y-%H%M%S")
        
        full_path = ""
        filename = ""
        if method == 'preview':
            if not os.path.exists(PREVIEW_DIR):
                os.makedirs(PREVIEW_DIR)
            filename = f"photo_{timestamp}.jpeg"
            full_path = os.path.join(PREVIEW_DIR, filename)
            with open(full_path, "wb") as file:
                file.write(image_data)
            
            # Add watermark to the preview image
            preview_image = Image.open(full_path)
            draw = ImageDraw.Draw(preview_image)
            watermark_text = "PREVIEW ONLY"
            font = ImageFont.load_default(45)
            colour = (255, 255, 255)
            draw.text((10, 10), watermark_text, fill=colour, font=font)
            preview_image.save(full_path, "JPEG")
            
            # Store the filename in the session for later use
            session['preview_image_filename_url'] = full_path 
            session['preview_image_filename'] = filename
            return jsonify({"preview_image_filename": filename}), 200
                
        elif method == 'full':
            if not os.path.exists(PHOTO_DIR):
                os.makedirs(PHOTO_DIR)
            filename = f"photo_{timestamp}.png"
            full_path = os.path.join(PHOTO_DIR, filename)
            with open(full_path, "wb") as file:
                file.write(image_data)
                
            # Generate unique code for the photo
            chars = string.ascii_uppercase + string.digits
            unique_code = ''.join(secrets.choice(chars) for _ in range(6))
            photo_frame = session.get('photo_size')
            
            # Save the photo to the database
            photo = Photo(path="/" + full_path,
                          filename=f"photo_{timestamp}.png",
                          unique_code=unique_code,
                          frame="7 cm x 10 cm" if photo_frame == "frame1" else "14 cm x 10 cm",
                          date_of_save=datetime.now(UTC) + timedelta(hours=8))  # Timezone adjustment for UTC+8
            db.session.add(photo)
            db.session.commit()
            
            # Store the filename in the session for later use
            session['full_image_filename_url'] = full_path 
            session['full_image_filename'] = filename
            
            return jsonify({"full_image_filename": filename}), 200
        
    except Exception as e:
        print(f"❌ Error saving photo: {e}")
        return jsonify({"error": str(e)}), 500
      
    
# Capture Photo 
@app.route('/save_image', methods=['POST'])
def save_image():
    """Save the captured image from the request to the server.

    Returns:
        Response: JSON response with the filename of the saved image or an error message.
    """
    try:
        # Check if the session already has an image filename
        #if 'full_image_filename' in session:
        #    print("Image filename already exists in session:", session['full_image_filename'])
        #    return jsonify({"full_image_filename": session.get("full_image_filename")}), 200
        
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
            
        if not os.path.exists(PREVIEW_DIR): 
            os.makedirs(PREVIEW_DIR)
        
        image_data = base64.b64decode(base64_image)
        timestamp = time.strftime("%d%m%Y-%H%M%S")
        hd_filename = f"{PHOTO_DIR}/photo_{timestamp}.png"
        preview_filename = f"{PREVIEW_DIR}/photo_{timestamp}.jpeg"
        
        with open (hd_filename, "wb") as file:
            file.write(image_data)
            
        with open(preview_filename, "wb") as file:
            file.write(image_data)
        
        print(f"HD Photo captured and saved as {hd_filename}")
        print(f"Preview Photo captured and saved as {preview_filename}")
        
        preview_image = Image.open(preview_filename)
        draw = ImageDraw.Draw(preview_image)
        watermark_text = "PREVIEW ONLY"
        font = ImageFont.load_default(45)
        colour = (255, 255, 255)
        
        draw.text((10, 10), watermark_text, fill=colour, font=font)
        preview_image.save(preview_filename, "JPEG")
        
        # Generate unique code for the photo
        chars = string.ascii_uppercase + string.digits
        unique_code = ''.join(secrets.choice(chars) for _ in range(6))
        photo_frame = session.get('photo_size')
        
        # Save the photo to the database
        photo = Photo(path="/" + hd_filename, filename=f"photo_{timestamp}.png" , unique_code=unique_code, frame="7 cm x 10 cm" if photo_frame == "frame1" else "14 cm x 10 cm", date_of_save=datetime.now(UTC) + timedelta(hours=8))  # Adjust for timezone if needed
        db.session.add(photo)
        db.session.commit()
        
        # Store the filename in the session for later use
        session['preview_image_filename_url'] = preview_filename # This is solely for preview purposes
        session['full_image_filename_url'] = hd_filename  # This is the HD photo
        session['full_image_filename'] = f"photo_{timestamp}.png"
        
        return jsonify({"full_image_filename": f"photo_{timestamp}.png"}), 200
    
    except Exception as e:
        print(f"❌ Error saving photo: {e}")
        return jsonify({"error": str(e)}), 500
        

# Exit function
@app.route('/exit')
def exit_app():
    """Exit the application, clearing data with pending status at this stage, and clear session data.

    Returns:
        Response: Redirects to the index page after clearing session data.
    """
    
    # Check if the current photo exists with pending status in the database and delete it
    
    full_image_filename = session.get('full_image_filename')  # Get the current photo filename from the session
    full_hd_photo_path = session.get('full_image_filename_url')
    full_preview_photo_path = session.get('preview_image_filename_url')

    # Process of deleting the photo only for pending status (if the customer leaves the page without payment)
    current_photo = Photo.query.filter_by(filename=full_image_filename, status=PhotoStatus.PENDING).first()
    
    if current_photo:
        print(f"Current photo found: {current_photo.path}")
        db.session.delete(current_photo)  # Delete the photo from the database
        db.session.commit()
        
        # Remove the HD photo from the server if it exists
        if os.path.exists(full_hd_photo_path):
            os.remove(full_hd_photo_path)
            print(f"HD photo {full_hd_photo_path} deleted from server.")
        
        # Remove the preview photo from the server if it exists
        if os.path.exists(full_preview_photo_path):
            os.remove(full_preview_photo_path)
            print(f"Preview photo {full_preview_photo_path} deleted from server.")
    
    # Clear the session data
    clear_session()
    print("Exiting the application and clearing session data..")
    
    # Redirect to the index page
    return redirect(url_for('index'))

# Failure function
@app.route('/fail')
def fail():
    """Handle payment failure by rendering the fail page.

    Returns:
        Response: Rendered HTML template for the fail page.
    """
    status = request.args.get("status")
    
    # Get the payment ID from the request or session
    payment_id = request.args.get("payment_request_id") or session.get("payment_request_id") # or get_last_item_from_store()
    current_photo = Photo.query.filter_by(filename=session.get('full_image_filename')).first()  # Get the current photo from the database
    if current_photo:
        print(f"Current photo found: {current_photo.path}")
        current_photo.status = PhotoStatus.FAILED
        db.session.commit()
    else:
        print("❌ Current photo not found in database.")
    print(f"Status: '{status}'")        # Debug
    print(f"Payment ID: '{payment_id}'")  # Debug
    if status not in ['canceled', 'failed', 'unknown'] or not payment_id:
        abort(403)
    print("Payment failed!")
    return render_template('fail.html', index=False)

# View payment page
@app.route('/payment', methods=['POST'])
def payment():
    """View payment page and save the image.

    Returns:
        Response: Redirects to the payment summary page after saving the image.
    """
    
    # Save the image
    save_image()
    return redirect(url_for('payment_summary'))

# View payment summary
@app.route('/payment-summary')
def payment_summary():
    """View the payment summary page with frame data and price.

    Returns:
        Response: Rendered HTML template for the payment summary page.
    """
    frame_data = ""
    price = ""
    if 'session' not in globals() or 'photo_size' not in session:
        print("❌ No photo size selected in session.")
        abort(404)
    selected_size = session.get('photo_size')
    if selected_size == "frame1":
        frame_data = "7 cm x 10 cm"
        price = "10.00"  
    elif selected_size == "frame2":
        frame_data = "14 cm x 10 cm" 
        price = "20.00"
        
    # Store the frame data and price in the session    
    session['frame_data'] = frame_data
    session['price'] = price 
    photo_width = session.get('image_width')
    photo_height = session.get('image_height')
    photo_filename = session.get('preview_image_filename_url')  # This is the preview image filename
    
    if photo_width is None or photo_height is None or photo_filename is None:
        print("❌ Missing photo dimensions or filename in session.")
        abort(404)
        
    print(f"Photo width: {photo_width}, height: {photo_height}, filename: {photo_filename}")  # Debug
    
    return render_template('payment.html', frame_data=frame_data, price=price, selected_size=selected_size, photo_width=photo_width, photo_height=photo_height, photo_filename=photo_filename, index=False) 
    
@app.route('/create-payment-request')
def create_payment_request():
    """Create a payment request using the Hitpay API.

    Returns:
        Response: JSON response containing payment data or an error message.
    """
    frame_data = session.get('frame_data')
    if not frame_data:
        return jsonify({"error": "Frame data not found in session"}), 400
    
    price = session.get('price')
    if not price:
        return jsonify({"error": "Price not found in session"}), 400
    
    reference_id = str(uuid.uuid4())
    url = "https://api.sandbox.hit-pay.com/v1/payment-requests"
    redirect_url = "https://fun-pony-engaging.ngrok-free.app/redirect"
    
    headers = {
        "X-BUSINESS-API-KEY": HITPAY_API_KEY,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    payload = {
        "amount": str(price),                                                                       # Example amount for testing, adjust as needed
        "currency": "SGD",                                                                          # For testing, use SGD. Other currencies not supported in sandbox
        "purpose": frame_data + " frame photo",                                                     # Description of the payment
        "redirect_url": redirect_url,                                                               # Redirect URL after payment
        "webhook": "https://fun-pony-engaging.ngrok-free.app/payment-confirmation/webhook",         # Webhook URL for payment confirmation
        "reference": reference_id,
        "send_email": False                                                                          # Send email notification
    }

    response = requests.post(url, headers=headers, data=payload, timeout=10) 

    if response.status_code == 201:
        payment_data = response.json()
        payment_database = Payment(
            payment_request_id=payment_data.get('id'),
            status='pending',
            frame=frame_data,
            price=float(price), 
            start_time=datetime.now(UTC) + timedelta(hours=8),
            end_time=datetime.now(UTC) + timedelta(hours=8) + timedelta(minutes=10) # Set end time to 10 minutes later to avoid null error
        )
        db.session.add(payment_database)
        db.session.commit()
        return payment_data
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to create payment",
            "error_detail": response.text
        }), response.status_code
             
@app.route('/success')
def success():
    """Render the success page after a successful payment and generate QR code with link to the saved image.

    Returns:
        Response: Rendered HTML template for the success page with QR code.
    """
    
    # Check if the payment was successful
    status = request.args.get("status")
    payment_id = request.args.get("payment_request_id")
    print(f"Status: '{status}'")                  # Debug
    print(f"Payment Request ID: '{payment_id}'")  # Debug
    
    # Check if the payment status is valid
    if status not in ['succeeded'] or not payment_id:
        abort(403)   # Forbidden
        
    # Check that the payment_id exists in session or database
    if not payment_id or payment_id != session.get('payment_request_id'):
        abort(403)  # Forbidden
           
    #stored_status = get_status(payment_id)  # Check if the payment ID exists in the store
    stored_payment = Payment.query.filter_by(payment_request_id=payment_id).first()  # Check if the payment ID exists in the database
    if not stored_payment:
        print(f"Payment ID {payment_id} not found in database.")
        return redirect(url_for('fail', payment_request_id=payment_id, status='failed'))
    
    stored_status = stored_payment.status
    
    if not stored_status or stored_status != 'succeeded':
        print(f"Payment ID {payment_id} not found or not succeeded.")
        return redirect(url_for('fail', payment_request_id=payment_id, status='failed'))
        
    image_filename_with_url = session.get('full_image_filename_url')  # Get the full image filename with URL from the session
    image_filename = session.get('full_image_filename')
    image_url = "/" + session.get('full_image_filename_url')  # Get the full image URL from the session
    preview_image_url = session.get('preview_image_filename_url')  # Get the preview image URL from the session
    
    # Check if the image URL is valid
    current_photo = Photo.query.filter_by(path=image_url).first()  
    if current_photo:
        print(f"Current photo found: {current_photo.path}")
        current_photo.status = PhotoStatus.PAID
        db.session.commit()
    else:
        print("❌ Current photo not found in database.") 
    print(f"Image URL: {image_url}")  # Debug
    
    # Remove the preview image from the server
    if os.path.exists(preview_image_url):
        os.remove(preview_image_url)  # Remove the preview image from the server     
    
    if image_url:
        secure_url = get_secure_image_url(image_filename, add_expiration=True, download=True)
        print(f"Secure URL generated: {secure_url}")
        qr = qrcode.QRCode(version=1, box_size=6, border=4)
        qr.add_data(secure_url)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        
        # Save QR code to a bytes buffer
        buffer = BytesIO()
        img.save(buffer, "PNG")
        buffer.seek(0)
        
        # Convert QR code to base64 for embedding in HTML
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('ascii')
        #print(f"QR code base64: {qr_base64}")
        
    return render_template('success.html', qr_code=qr_base64, index=False, photo=current_photo)
        
@app.route('/pay', methods=['POST'])
def pay():
    """Create a payment token and redirect to the Hitpay payment page.

    Returns:
        Response: JSON response containing the payment URL or an error message.
    """
    try:
        # Create a unique payment token
        payment_token = secrets.token_urlsafe(16)
        
        # Store the payment token and data from before into the server
        session['payment_token'] = payment_token
        session['original_session'] = session.copy() # Store the original session data
        print(f"Payment token created: {payment_token}")
        
        # Create a payment request and redirect to the payment URL
        payment_request = create_payment_request()
        
        # Extract the payment URL from the response
        payment_url = payment_request.get('url') 
        print(f"Payment URL: {payment_url}")
        
        if payment_url:
            # Return payment url
            return jsonify({"redirect_url": payment_url, "payment_token": payment_token}), 200
        else:
            return jsonify({"error": "Failed to create payment request"}), 400
        
    except Exception as e:
        print("❌ Internal Server Error:", e)
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500    
    
# Webhook for payment status
@app.route('/payment-confirmation/webhook', methods=['POST'])
def webhook():
    """Handle the Hitpay webhook for payment confirmation.

    Returns:
        Response: JSON response indicating the status of the payment or an error message.
    """
    raw_body = request.get_data()
    test_data = request.data
    print("Received:", raw_body)
    
    signature = request.headers.get('Hitpay-Signature', '')
    event_type = request.headers.get('Hitpay-Event-Type')
    event_obj = request.headers.get('Hitpay-Event-Object')
    
    # Check if the event type and object are valid
    if not signature:
        return jsonify({"error": "No signature provided"}), 400
 
    # Verify the Hitpay signature
    if not verify_hitpay_signature(test_data, signature, HITPAY_SALT):
        print("❌ Invalid signature")
        payment_id = request.json.get('id')
        payment_request_id = request.json.get('payment_request_id')
        #payment_status_store[payment_request_id] = {
        #        "payment_id": payment_id,
        ##        "status": "failed",
        #       "timestamp": datetime.now().isoformat()
        #}
        # save_status(payment_request_id, payment_id, 'failed')
        current_payment = Payment.query.filter_by(payment_request_id=payment_request_id).first()
        if current_payment:         # Update the payment status in the database
            current_payment.status = 'failed'
            current_payment.payment_id = payment_id
            current_payment.end_time = datetime.now(UTC) + timedelta(hours=8)
            db.session.commit()
        session['payment_request_id'] = payment_request_id
        return jsonify({"status": "failed", "message": "Invalid Signature"}), 400
    
    # Extract payment ID and status from the payload
    payload = request.get_json()
    
    # Process the webhook event
    print(f"Received event {event_type} on object {event_obj}: {payload}")
    
    # Check if the payload is empty
    if not payload:
        print("❌ No payload received")
        return jsonify({"error": "No payload received"}), 400
    
    payment_id = payload.get('id')
    payment_request_id = payload.get('payment_request_id')
    status = payload.get('status')
    
    # Check the payment status
    if payment_id and status:
        print(f"Payment ID: {payment_id}, Status: {status}")
        
        # If payment is successful, redirect to success page
        if status == 'succeeded':
            print("Payment successful!")
            print(f"Stored payment {payment_id} = {status}")
            #payment_status_store[payment_request_id] = {
            #    "payment_id": payment_id,
            #    "status": status,
            #    "timestamp": datetime.now().isoformat()
            #}
            # save_status(payment_request_id=payment_request_id, payment_id=payment_id, status='succeeded')
            current_payment = Payment.query.filter_by(payment_request_id=payment_request_id).first()
            if current_payment:
                current_payment.status = status  
                current_payment.payment_id = payment_id
                current_payment.end_time = datetime.now(UTC) + timedelta(hours=8)
                db.session.commit()
            session['payment_request_id'] = payment_request_id
            return jsonify({"status": "success", "message": "Payment successful"}), 200
        else:
            print("Payment failed or pending.")
            return jsonify({"status": "failed", "message": "Payment failed or pending"}), 400
        
@app.route('/payment-status', methods=['GET'])
def payment_status():
    """Retrieve the payment status based on the payment request ID.

    Returns:
        Response: JSON response containing the payment status or an error message.
    """
    payment_request_id = request.args.get('payment_request_id')
    
    if not payment_request_id:
        return jsonify({"error": "Payment Request ID is required"}), 400
    
    # Check if the payment ID exists in the store
    record = Payment.query.filter_by(payment_request_id=payment_request_id).first()  
    if not record:
        print(f"Payment Request ID {payment_request_id} not found in database.")
        return jsonify({"error": "Payment Request ID not found"}), 404
    
    # Get the status from the record
    status = None
    if record:
        status = record.status

    if status:
        print(f"Payment ID: {payment_request_id}, Status: {status}")
        session["payment_request_id"] = payment_request_id
        return jsonify({"payment_request_id": payment_request_id, "status": status}), 200
    else:
        return jsonify({"payment_request_id": payment_request_id, "status": "pending"}), 404    

# Redirect user either success page or failed page
@app.route('/redirect', methods=['GET'])
def redirect_user():
    """Redirect user to the success or fail page based on the payment status.
       This function will be called after the payment is completed or cancelled from Hitpay.

    Returns:
        Response: Rendered HTML template for the redirect page with payment status.
    """
    
    payment_request_id = request.args.get('reference')
    status_param = request.args.get('status')
    
    # Check if the payment token exists in the session
    if 'payment_token' not in session:
        return "Invalid session token", 400
    
    original_data = session.get('original_session', {})
    session.update(original_data)  # Restore original session
    session.pop('payment_token', None)
    session.pop('original_session', None)
    
    # DEBUG: Test data from original session
    print("Session data: ", session.get('session_id'))
    print("Current selected frame: " + session.get('frame_data'))
    
    # Store payment request ID. This will be used to save the payment status
    if status_param == 'canceled':
        save_status(payment_request_id=payment_request_id, payment_id='None', status='canceled')
        current_payment = Payment.query.filter_by(payment_request_id=payment_request_id).first()
        current_photo = Photo.query.filter_by(filename=session.get('full_image_filename')).first()
        if current_payment:
            current_payment.status = 'canceled'
            current_payment.end_time = datetime.now(UTC) + timedelta(hours=8)
            db.session.commit()
            
        if current_photo:
            current_photo.status = PhotoStatus.CANCELED
            db.session.commit()
  
    print(request.args.to_dict())
    return render_template('redirect.html', payment_request_id=payment_request_id, payment_status=status_param, index=False)

@app.route('/admin/download', methods=['GET'])
def admin_download():
    """Render the admin page with payment status store (ADMIN ONLY).

    Returns:
        Response: Rendered HTML template for the admin page with payment status store.
    """
    if session.get("is_admin") != True:
        return redirect(url_for("admin_login"))
    
    return render_template('admin_download.html', index=False)

@app.route('/download', methods=['POST'])
def download():
    """Download the HD photo image from customer's unique code (ADMIN ONLY).

    Returns:
        Response: View the HD photo image as an attachment.
    """
    unique_code = request.json.get("unique_code", "").strip().upper()
    
    if not unique_code:
        return jsonify({"error": "Unique Code is Required"}), 400
    
    # Query the photo from the database using the unique code
    photo = Photo.query.filter_by(unique_code=unique_code).first()
    if not photo:
        return jsonify({"error": "Photo Not found"}), 404
    
    photo_status = photo.status
    
    # Check if the photo status is PAID
    match photo_status:
        case PhotoStatus.PAID:
            print(f"Photo with unique code {unique_code} is paid.")
        case PhotoStatus.EXPIRED:
            return jsonify({"error": "The Photo has Expired. Unable to Download."}), 403
        case PhotoStatus.FAILED:
            return jsonify({"error": "The Photo's Payment Failed. Unable to Download."}), 403
        case PhotoStatus.CANCELED:
            return jsonify({"error": "The Photo's Payment was Canceled. Unable to Download."}), 403
        case _:
            return jsonify({"error": "Invalid Photo Status. Unable to Download."}), 403
    
    # Generate secure URL for the photo
    photo_filename = photo.filename
    secure_url = get_secure_image_url(photo_filename, add_expiration=False, download=False)
    
    # Send the file as an attachment
    return jsonify(success=True, url=secure_url) 

# Testing page (Only for development purposes)
@app.route('/test')
def test():
    return render_template('test.html', index=False)


if __name__ == '__main__':
    app.run(debug=True)

