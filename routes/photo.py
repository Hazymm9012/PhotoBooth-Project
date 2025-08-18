from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify, current_app, send_file
from models import Photo, db, PhotoStatus
from datetime import datetime, timedelta, UTC
from PIL import Image, ImageDraw, ImageFont
from utils import encode_image, encode_image_to_data_url

import jwt
import base64
import time
import string
import secrets
import requests
import os
import socket

# Blueprint for photo-related routes
bp = Blueprint("photo", __name__)

# Choose print size for photo
@bp.route('/choose_size')
def choose_size():
    """Render the choose size page for the photo.

    Returns:
        str: Rendered HTML template for the choose size page.
    """
    return render_template('chooseSize.html', index=False)

# Set print size of the photo
@bp.route('/set_size', methods=['POST'])
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
    
    return redirect(url_for('photo.preview'))

# Preview page
@bp.route('/preview')
def preview():
    """Render the preview page with the photo width and height.

    Returns:
        str: Rendered HTML template for the preview page.
    """
    
    photo_session = session.get('preview_image_filename')
    
    # TEMPORARY SOLUTION (This will cause bug when user goes back to set size page)
    photo_width = session.get('image_width')
    photo_height = session.get('image_height')
    img_ratio = photo_width / photo_height if photo_height else None
    
    # If the photo session is available, restore the session
    if photo_session:
        print("Session photo data found:", photo_session)
        old_photo_size = session.get('old_photo_size')
        return render_template(
            'preview.html',
            photo_width=photo_width,
            photo_height=photo_height,
            session_id=session['session_id'],
            img_ratio=img_ratio,
            photo_session=photo_session,
            old_photo_size=old_photo_size,
            index=False
        )
            
    # Check if the width and height of the preview camera are available
    if photo_width is None or photo_height is None:
        return "Photo width and Photo height are required", 403
    
    print(f"Retrieved values: width {photo_width}, height {photo_height}")
    return render_template(
        'preview.html',
        photo_width=photo_width,
        photo_height=photo_height,
        session_id=session['session_id'],
        img_ratio=img_ratio,
        index=False
    )

@bp.route('/upload', methods=['POST'])
def upload():
    """Upload an image and generate a pixar-style photo using the ChatGPT/Together API.
    
    Returns:
        Response: JSON response containing the generated image URL or an error message.
    """
    try:
        # Initialize OpenAI client
        client = current_app.config["OPENAI_CLIENT"]
        if not client:
            return jsonify({"error": "OpenAI client cannot be initialized"}), 500        
        
        # Request data from the client
        data = request.get_json()
        
        # Check if the data contains the image and background filename
        if not data or 'image' not in data:
            print("❌ No image data provided.")
            return "No image data provided", 400
        
        # Encode the image and background image to base64
        encoded_background_image = encode_image(
            os.path.join("static/images/", data.get("background_filename"))
        )
        encoded_image = encode_image_to_data_url(data.get("image"))
        
        # Retrieve current session requested photo width and height
        photo_size = session.get('photo_size')
        
        # Set the prompt text for the image generation
        prompt_text = (
            "Change the style of this image into a 3D pixar-style image. "
            "Use the second image as the background image for the first image. "
            "Make it look cartoonish."
        )
        
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
            }],
            tools=[{
                "type": "image_generation",
                "size": "1024x1536" if photo_size == "frame1" else "1536x1024",
                "quality": "medium",  # medium quality for faster response
            }],
        )
        
        # DEBUG: Print the response from the API
        print("Image has been successfully generated.")
        
        # Extract the image URL
        image_outputs = [
            output for output in response.output 
            if output.type == "image_generation_call"
        ]
        if image_outputs:
            image_base64 = image_outputs[0].result  
            image_url = f"data:image/png;base64,{image_base64}"
            return jsonify({"image_url": image_url})
        else:
            return jsonify({"error": "No image generated"}), 400
    except requests.exceptions.Timeout:
        print("❌ Request to OpenAI timed out")
        return jsonify({"error": "The request to OpenAI timeout"}), 503
    
    except requests.exceptions.ConnectionError:
        print("❌ Network error")
        return jsonify({"error": "Network Connection Error"}), 503
    
    except socket.timeout:
        print("❌ Socket timeout")
        return jsonify({"error": "Socket Timeout"}), 504
    
    except Exception as e:
        print(f"❌ API Error: {e}")
        return jsonify({"error": str(e)}), 500
    
# Capture Photo 
@bp.route('/save_image', methods=['POST'])
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
        photo_dir = current_app.config["PHOTO_DIR"]
        preview_dir = current_app.config["PREVIEW_DIR"]
        
        if not image_data:
            return jsonify({'error': 'No Image Provided'}, 400)
        
        try:
            header, base64_image = image_data.split(',', 1)
        except ValueError:
            return jsonify({'error': 'Invalid base64 image format'}), 400
        
        if not os.path.exists(photo_dir):
            os.makedirs(photo_dir)
            
        if not os.path.exists(preview_dir): 
            os.makedirs(preview_dir)
        
        image_data = base64.b64decode(base64_image)
        timestamp = time.strftime("%d%m%Y-%H%M%S")
        hd_filename = f"{photo_dir}/photo_{timestamp}.png"
        preview_filename = f"{preview_dir}/photo_{timestamp}.jpeg"
        
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
        
        # Store the preview photo filename in the session
        session['preview_image_filename_url'] = preview_filename # This is solely for preview purposes
        session['preview_image_filename'] = f"photo_{timestamp}.jpeg"
        
        # Store the HD photo filename in the session
        session['full_image_filename_url'] = hd_filename  # This is the HD photo
        session['full_image_filename'] = f"photo_{timestamp}.png"
        
        return jsonify({"preview_image_filename_url": preview_filename}), 200
    
    except Exception as e:
        print(f"❌ Error saving photo: {e}")
        return jsonify({"error": str(e)}), 500

# Delete current photo
@bp.route('/delete_photo', methods=['POST'])
def delete_photo():
    """Delete the current photo from the server and database.
    Returns:
        Response: JSON response indicating success or failure of the deletion.
    """
    full_image_filename = session.get('full_image_filename')
    full_hd_photo_path = session.get('full_image_filename_url')
    full_preview_photo_path = session.get('preview_image_filename_url')
    if not full_image_filename or not full_hd_photo_path or not full_preview_photo_path:
        return jsonify({"error": "No photo to delete"}), 400
    try:
        # Check if the current photo exists in the database and delete it
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
                
            # Clear session data related to the photo
            session.pop('full_image_filename', None)
            session.pop('full_image_filename_url', None)
            session.pop('preview_image_filename', None)
            session.pop('preview_image_filename_url', None)
            
            return jsonify({"message": "Photo deleted successfully"}), 200
        else:
            print("❌ Current photo not found in database.")
            return jsonify({"error": "Photo not found"}), 404  
    except Exception as e:
        print(f"❌ Error deleting photo: {e}")
        return jsonify({"error": str(e)}), 500  
    
# View secure image
@bp.route('/view-secure-image')
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
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=['HS256'])
        image_filename = payload.get('image_filename')
        full_path = os.path.join(current_app.config["PHOTO_DIR"], image_filename)
        
        # Check if the image exists
        if not full_path or not os.path.exists(full_path):
            return "Image not found", 404
        
        # Send the image file
        return send_file(full_path, as_attachment=download)
    
    except jwt.ExpiredSignatureError:
        return "Token has expired", 403
    except jwt.InvalidTokenError:
        return "Invalid token", 403
