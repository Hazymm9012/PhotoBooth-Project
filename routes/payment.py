from flask import Blueprint, redirect, url_for, render_template, session, abort, current_app, jsonify, request
from utils import verify_hitpay_signature, get_secure_image_url
from models import Photo, PhotoStatus, Payment, db  
from datetime import datetime, timedelta, UTC
from io import BytesIO

import qrcode
import base64
import requests
import uuid
import os
import secrets


bp = Blueprint("payment", __name__)


# View payment page
@bp.route('/payment', methods=['POST'])
def payment():
    """View payment page and save the image.

    Returns:
        Response: Redirects to the payment summary page after saving the image.
    """
    
    # Save the image
    #save_image_file('preview')  # Save the preview image file (this is temporary)
    #save_image_file('full')  # Save the full image file
    #save_image()
    return redirect(url_for('payment.payment_summary'))

# View payment summary
@bp.route('/payment-summary')
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
        
    print(f"Photo width: {photo_width}, height: {photo_height}, "
          f"filename: {photo_filename}")  # Debug
    
    return render_template('payment.html', frame_data=frame_data, 
                           price=price, selected_size=selected_size, 
                           photo_width=photo_width, 
                           photo_height=photo_height, 
                           photo_filename=photo_filename, index=False) 
    
@bp.route('/create-payment-request')
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
    url = current_app.config["HITPAY_URL"]                                          # Use the Hitpay URL from the config
    redirect_url = url_for("payment.redirect_user", _external=True)                       # Use the Hitpay redirect URL from the config
    
    headers = {
        "X-BUSINESS-API-KEY": current_app.config["HITPAY_API_KEY"],                 # Use the Hitpay API key from the config
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    payload = {
        "amount": str(price),                                                       # Example amount for testing, adjust as needed
        "currency": "SGD",                                                          # For testing, use SGD. Other currencies not supported in sandbox
        "purpose": frame_data + " frame photo",                                     # Description of the payment
        "redirect_url": redirect_url,                                               # Redirect URL after payment
        "webhook": current_app.config["BASE_URL"] + "/payment-confirmation/webhook",# Webhook URL for payment confirmation
        "reference": reference_id,
        "send_email": False                                                         # Send email notification
    }

    # Send post request to Hitpay API to create payment request
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
        
@bp.route('/pay', methods=['POST'])
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
@bp.route('/payment-confirmation/webhook', methods=['POST'])
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
    if not verify_hitpay_signature(test_data, signature, current_app.config["HITPAY_SALT"]):
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
        
@bp.route('/payment-status', methods=['GET'])
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
    
# Failure function
@bp.route('/fail')
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
        
        # Update the status of the current photo to FAILED or CANCELED
        if status == 'canceled':
            current_photo.status = PhotoStatus.CANCELED
        else:
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
             
@bp.route('/success')
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
        abort(500)   # Internal Server Error
        
    # Check that the payment_id exists in session or database
    if not payment_id or payment_id != session.get('payment_request_id'):
        abort(500)  # Internal Server Error
           
    #stored_status = get_status(payment_id)  # Check if the payment ID exists in the store
    stored_payment = Payment.query.filter_by(payment_request_id=payment_id).first()  # Check if the payment ID exists in the database
    if not stored_payment:
        print(f"Payment ID {payment_id} not found in database.")
        return redirect(url_for('payment.fail', payment_request_id=payment_id, status='failed'))
    
    stored_status = stored_payment.status
    
    if not stored_status or stored_status != 'succeeded':
        print(f"Payment ID {payment_id} not found or not succeeded.")
        return redirect(url_for('payment.fail', payment_request_id=payment_id, status='failed'))
        
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
    
    qr_base64 = None
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


# Redirect user either success page or failed page
@bp.route('/redirect', methods=['GET'])
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
        # save_status(payment_request_id=payment_request_id, payment_id='None', status='canceled')
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