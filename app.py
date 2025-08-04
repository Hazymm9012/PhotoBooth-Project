import uuid
from flask import Flask, abort, render_template, request, redirect, url_for, session, jsonify, send_file
from together import Together
from tkinter import *
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from utils import  encode_image, is_valid_base64, encode_image_to_data_url, get_local_ip, verify_hitpay_signature, clear_session
from payment_status_store import load_status_store, save_status, get_status, get_last_item_from_store
from openai import OpenAI
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv

import os
import time
import base64 
import requests
import qrcode
import jwt
import secrets

# Load environment variables from .env file
load_dotenv() 

app = Flask(__name__)
app.config['SERVER_NAME'] = None
app.config['SESSION_COOKIE_SECURE'] = True

# Ensure app, openai, hitpay salt and api keys are set up in .env
app.secret_key = os.environ.get('SECRET_KEY')
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
HITPAY_SALT = os.environ.get('HITPAY_SALT')
HITPAY_API_KEY = os.environ.get('HITPAY_API_KEY')
ALLOWED_IPS = ['202.168.65.122', '127.0.0.1']

# Constants and global variables
PHOTO_DIR = 'static/photos'
PREVIEW_DIR = 'static/previews'
payment_status_store = {}
load_status_store()

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
    client_ip = request.remote_addr
    if client_ip not in ALLOWED_IPS:
        print(f"Access denied for IP: {client_ip}")
        abort(403)

# Generate secure link for the image file
def get_secure_image_url(filename):
    # Create payload with image path and expiration time 
    payload = {
        "image_path": f"{filename}",
        "exp": datetime.now(UTC) + timedelta(minutes=10)  # expires in 10 mins
    }
    
    # Generate token
    token = jwt.encode(payload, app.secret_key, algorithm='HS256')
    token = token if isinstance(token, str) else token.decode("utf-8")
    
    # Create a secure link
    secure_link = url_for('view_secure_image', token=token, _external=True)
    return secure_link

# View secure image
@app.route('/view-secure-image')
def view_secure_image():
    token = request.args.get('token')
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
        return send_file(full_path, as_attachment=True)
    
    except jwt.ExpiredSignatureError:
        return "Token has expired", 403
    except jwt.InvalidTokenError:
        return "Invalid token", 403

# Home Page
@app.route('/')
def index():
    return render_template('index.html')

# Preview page
@app.route('/preview')
def preview():
    photo_width = session.get('image_width')
    photo_height = session.get('image_height')
    
    # Check if the width and height of the preview camera are available
    if photo_height is None or photo_height is None:
        return "Photo width and Photo height are required", 403
    
    print(f"Retrieved values: width {photo_width}, height {photo_height}")
    img_ratio = photo_width / photo_height
    return render_template('preview.html', photo_width=photo_width, photo_height=photo_height, session_id=session['session_id'], img_ratio=img_ratio)

# Choose print size for photo
@app.route('/choose_size')
def choose_size():
    return render_template('chooseSize.html')

# Set print size of the photo
@app.route('/set_size', methods=['POST'])
def set_size():
    
    # Get the selected size from the form
    image_width = 0
    image_height = 0
    selected_size = request.form.get('size')
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

# Upload and generate pixar-style photo
@app.route('/upload', methods=['POST'])
def upload():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            print("❌ No image data provided.")
            return "No image data provided", 400
        
        encoded_background_image = encode_image(os.path.join("static/images/", data.get("background_filename")))
        encoded_image = encode_image_to_data_url(data.get("image"))
        
        # Retrieve current session requested photo width and height
        photo_size = session.get('photo_size')
        
        #response = client.images.generate(
        #    model = "black-forest-labs/FLUX.1-kontext-dev",
        #    width = photo_width,
        #    height = photo_height,
        #    prompt = "Change this image into a pixar-style image. Change all the background into pixar-style at the disney castle",
        #    image_url = data.get("image"),
        #)
        
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
        
        #if not response or not response.get('image_url'):
        #    raise Exception("Failed to generate image.")
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
            
        if not os.path.exists(PREVIEW_DIR): 
            os.makedirs(PREVIEW_DIR)
        
        image_data = base64.b64decode(base64_image)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
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
        
        # Store the filename in the session for later use
        session['image_filename_with_url'] = f"previews/photo_{timestamp}.jpeg" # This is solely for preview purposes
        session['image_filename'] = f"photo_{timestamp}.png"
        
        return jsonify({"image_filename": f"photo_{timestamp}.png"}), 200
    
    except Exception as e:
        print(f"❌ Error saving photo: {e}")
        return jsonify({"error": str(e)}), 500
        

# Exit function
@app.route('/exit')
def exit_app():
    clear_session()
    print("Exiting the application and clearing session data..")
    return redirect(url_for('index'))

# Failure function
@app.route('/fail')
def fail():
    status = request.args.get("status")
    
    # Get the payment ID from the request or session
    payment_id = request.args.get("payment_request_id") or session.get("payment_request_id") # or get_last_item_from_store()
    print(f"Status: '{status}'")        # Debug
    print(f"Payment ID: '{payment_id}'")  # Debug
    if status not in ['canceled', 'failed', 'unknown'] or not payment_id:
        abort(403)
    print("Payment failed!")
    return render_template('fail.html')

# View payment page
@app.route('/payment', methods=['POST'])
def payment():
    data = request.get_json()
    # print("Received data for payment:", data)  # Debug
    # session['photo_src'] = data.get('photo_src')
    
    # Save the image data to a file
    save_image()
    return redirect(url_for('payment_summary'))

# View payment summary
@app.route('/payment-summary')
def payment_summary():
    frame_data = ""
    price = ""
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
    photo_filename = session.get('image_filename_with_url') 
    
    if photo_width is None or photo_height is None or photo_filename is None:
        print("❌ Missing photo dimensions or filename in session.")
        abort(404)
        
    print(f"Photo width: {photo_width}, height: {photo_height}, filename: {photo_filename}")  # Debug
    
    return render_template('payment.html', frame_data=frame_data, price=price, selected_size=selected_size, photo_width=photo_width, photo_height=photo_height, photo_filename=photo_filename) 
    

# Send request to Hitpay API 
# API key needs to be set in the environment variables
@app.route('/create-payment-request')
def create_payment_request():
    frame_data = session.get('frame_data')
    if not frame_data:
        return jsonify({"error": "Frame data not found in session"}), 400
    
    price = session.get('price')
    if not price:
        return jsonify({"error": "Price not found in session"}), 400
    
    reference_id = str(uuid.uuid4())
    url = "https://api.sandbox.hit-pay.com/v1/payment-requests"
    redirect_url = "https://urchin-modest-instantly.ngrok-free.app/redirect"
    
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
        "webhook": "https://urchin-modest-instantly.ngrok-free.app/payment-confirmation/webhook",   # Webhook URL for payment confirmation
        "reference": reference_id,
        "send_email": True                                                                          # Send email notification
    }

    response = requests.post(url, headers=headers, data=payload, timeout=10) 

    if response.status_code == 201:
        payment_data = response.json()
        return payment_data
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to create payment",
            "error_detail": response.text
        }), response.status_code
             
# Generate QR code after payment for the image
@app.route('/success')
def success():
    # Check if the payment was successful
    status = request.args.get("status")
    payment_id = request.args.get("payment_request_id")
    print(f"Status: '{status}'")        # Debug
    print(f"Payment Request ID: '{payment_id}'")  # Debug
    
    # Check if the payment status is valid
    if status not in ['succeeded'] or not payment_id:
        abort(403)   # Forbidden
        
    # Check that the payment_id exists in session or database
    valid_payment_id = get_last_item_from_store()  # Example
    if not payment_id or payment_id != valid_payment_id:
        abort(403)  # Forbidden
           
    stored_status = get_status(payment_id)  # Check if the payment ID exists in the store
    
    if not stored_status or stored_status.get("status") != 'succeeded':
        print(f"Payment ID {payment_id} not found or not succeeded.")
        return redirect(url_for('fail', status='failed', payment_request_id=payment_id))
        
    image_filename_with_url = session.get('image_filename_with_url')
    image_filename = session.get('image_filename')
    image_url = url_for('static', filename=image_filename_with_url) if image_filename_with_url else None
    print(f"Image filename: {image_filename}")  # Debug
    
    if image_url:
        secure_url = get_secure_image_url(image_filename)
        print(f"Secure URL generated: {secure_url}")
        qr = qrcode.QRCode(version=1, box_size=6, border=4)
        qr.add_data(secure_url)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        
        # Save QR code to a bytes buffer
        buffer = BytesIO()
        img.save(buffer, "PNG")
        buffer.seek(0)
        #print(f"QR code generated for image: {secure_url}")
        
        # Convert QR code to base64 for embedding in HTML
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('ascii')
        #print(f"QR code base64: {qr_base64}")
        
    return render_template('success.html', qr_code=qr_base64)
        
# Payment through Hitpay website
@app.route('/pay', methods=['POST'])
def pay():
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
        payment_status_store[payment_request_id] = {
                "payment_id": payment_id,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
        }
        save_status(payment_request_id, payment_id, 'failed')
        session[payment_request_id] = payment_request_id
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
            payment_status_store[payment_request_id] = {
                "payment_id": payment_id,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            save_status(payment_request_id=payment_request_id, payment_id=payment_id, status='succeeded')
            return jsonify({"status": "success", "message": "Payment successful"}), 200
        else:
            print("Payment failed or pending.")
            return jsonify({"status": "failed", "message": "Payment failed or pending"}), 400
        
# Retrieve payment status
# Check from the store if the payment ID exists
@app.route('/payment-status', methods=['GET'])
def payment_status():
    payment_request_id = request.args.get('payment_request_id')
    
    if not payment_request_id:
        return jsonify({"error": "Payment ID is required"}), 400
    
    # Check if the payment ID exists in the store
    record = payment_status_store.get(payment_request_id)
    status = None
    if record:
        status = record.get('status')

    if status:
        return jsonify({"payment_request_id": payment_request_id, "status": status}), 200
    else:
        return jsonify({"payment_request_id": payment_request_id, "status": "pending"}), 404    

# Redirect user either success page or failed page
@app.route('/redirect', methods=['GET'])
def redirect_user():
    payment_request_id = request.args.get('reference')
    status_param = request.args.get('status')
    
    if 'payment_token' not in session:
        return "Invalid session token", 400
    
    original_data = session.get('original_session', {})
    session.update(original_data)  # Restore original session
    session.pop('payment_token', None)
    session.pop('original_session', None)
    
    # DEBUG: Test data from original session
    print("session data: ", session.get('session_id'))
    print("Current selected frame: " + session.get('frame_data'))
    
    # Store payment request ID. This will be used to save the payment status
    if status_param == 'canceled': 
        save_status(payment_request_id=payment_request_id, payment_id='None', status='canceled')
    
    print(request.args.to_dict())
    return render_template('redirect.html', payment_request_id=payment_request_id, payment_status=status_param)

# Testing page
@app.route('/test')
def test():
    return render_template('test.html')

if __name__ == '__main__':
    app.run(debug=True)

