import uuid
from flask import Flask, abort, render_template, request, redirect, url_for, session, jsonify, send_file
from together import Together
from tkinter import *
from PIL import Image, ImageTk
from io import BytesIO
from utils import  encode_image, is_valid_base64, encode_image_to_data_url, get_local_ip, verify_hitpay_signature, clear_session
from payment_status_store import load_status_store, save_status, get_status
from openai import OpenAI
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta, UTC

import os
import time
import base64 
import requests
import qrcode
import jwt

# Ensure the OpenAI, Hitpay salt is set up in environment variables
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_insecure_key')
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
HITPAY_SALT = os.environ.get('HITPAY_SALT')
PHOTO_DIR = 'static/photos'
payment_status_store = {}
load_status_store()
serializer = URLSafeTimedSerializer(app.secret_key)

# Generate secure link for the image file
def get_secure_image_url(filename):
    # Create payload with image path and expiration 
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
    print(f"Retrieved values: width {photo_width}, height {photo_height}")
    return render_template('preview.html', photo_width=photo_width, photo_height=photo_height)

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
        
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{PHOTO_DIR}/photo_{timestamp}.png"
        
        with open (filename, "wb") as file:
            file.write(base64.b64decode(base64_image))
        
        print(f"Photo captured and saved as {filename}")
        
        # Store the filename in the session for later use
        session['image_filename_with_url'] = f"photos/photo_{timestamp}.png"
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
    payment_id = request.args.get("payment_id")
    print(f"Status: '{status}'")        # Debug
    print(f"Payment ID: '{payment_id}'")  # Debug
    if status not in ['canceled', 'failed'] or not payment_id:
        abort(403)
    print("Payment failed!")
    return render_template('fail.html')

# View payment page
@app.route('/payment', methods=['POST'])
def payment():
    data = request.get_json()
    print("Received data for payment:", data)  # Debug
    # session['photo_src'] = data.get('photo_src')
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
    
    return render_template('payment.html', frame_data=frame_data, price=price, selected_size=selected_size)
    

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
    redirect_url = "https://fun-pony-engaging.ngrok-free.app/redirect"
    API_KEY = os.environ.get('HITPAY_API_KEY')
    
    headers = {
        "X-BUSINESS-API-KEY": API_KEY,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    payload = {
        "amount": str(price),                           # Example amount for testing, adjust as needed
        "currency": "SGD",                              # For testing, use SGD. Other currencies not supported in sandbox
        "purpose": frame_data + " frame photo",         # Description of the payment
        "redirect_url": redirect_url, 
        "webhook_url": "https://fun-pony-engaging.ngrok-free.app/payment-confirmation/webhook",
        "reference": reference_id, 
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
        
# Download image into URL 
#@app.route('/download_image')
#def download_image():
#    image_path = session.get('image_filename')
#    if os.path.exists(image_path):
#        return send_file(image_path, as_attachment=True)
#    return "Image not found", 404
             
# Generate QR code after payment for the image
@app.route('/success')
def success():
    
    # Check if the payment was successful
    status = request.args.get("status")
    payment_id = request.args.get("payment_id")
    print(f"Status: '{status}'")        # Debug
    print(f"Payment ID: '{payment_id}'")  # Debug
    
    # Check if the payment status is valid
    if status not in ['completed'] or not payment_id:
        abort(403)   # Forbidden
        
    # Check that the payment_id exists in session or database
    valid_payment_id = session.get('payment_id')  # Example

    if not payment_id or payment_id != valid_payment_id:
        abort(403)  # Forbidden
        
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
        # Create a payment request and redirect to the payment URL
        payment_request = create_payment_request()
        
        # Extract the payment URL from the response
        payment_url = payment_request.get('url') 
        print(f"Payment URL: {payment_url}")
        
        if payment_url:
            # Return payment url
            return jsonify({"redirect_url": payment_url})
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
        return jsonify({"error": "Invalid signature"}), 400
    
    # Process the webhook event
    payload = request.get_json()
    print(f"Received event {event_type} on object {event_obj}: {payload}")
    
    payment_id = payload.get('id')
    status = payload.get('status')
    
    # Check the payment status
    if payment_id and status:
        print(f"Payment ID: {payment_id}, Status: {status}")
        
        # If payment is successful, redirect to success page
        if status == 'succeeded':
            print("Payment successful!")
            print(f"Stored payment {payment_id} = {status}")
            payment_status_store[payment_id] = status
            save_status(payment_id, 'succeeded')
            return jsonify({"status": "success", "message": "Payment successful"}), 200
        else:
            print("Payment failed or pending.")
            return jsonify({"status": "failed", "message": "Payment failed or pending"}), 400

# Redirect user either success page or failed page
@app.route('/redirect', methods=['GET'])
def redirect_user():
    payment_id = request.args.get('reference')
    payment_status = payment_status_store.get(payment_id)
    
    # Store payment id to check later for verification
    session['payment_id'] = payment_id
    
    print(request.args.to_dict())
    return render_template('redirect.html', payment_id=payment_id, payment_status=payment_status)


if __name__ == '__main__':
    app.run(debug=True)

