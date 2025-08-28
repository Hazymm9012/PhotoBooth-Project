from flask import render_template, request, redirect, url_for, session, Blueprint, current_app
from tkinter import *
from utils import clear_session
from models import db
from models import Photo, PhotoStatus

import uuid
import os


bp = Blueprint("main", __name__, template_folder="templates", static_folder="static")

# Check session ID and create a new one if it doesn't exist
@bp.before_request
def ensure_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())  
        session['is_new_session'] = True
        print("New session created with ID:", session['session_id'])
    else:
        session['is_new_session'] = False

# Check if the request is from an allowed IP address.
# During development, use local IP address to the ALLOWED_IPS list.        
@bp.before_request
def limit_remote_address():
    """Check if the request is from an allowed IP address."""
    client_ip = request.remote_addr
    if client_ip not in current_app.config["ALLOWED_IPS"]:
        print(f"Access denied for IP: {client_ip}")
        return render_template('403.html'), 403

# Home Page
@bp.route('/')
def index():
    """Render the home page."""
    return render_template('index.html', index=True)


# Exit function
@bp.route('/exit')
def exit_app():
    """Exit the application, clearing data with pending status at this stage, and clear session data.

    Returns:
        Response: Redirects to the index page after clearing session data.
    """
    
    # Check if the current photo exists with pending status in the database and delete it
    full_image_original_filename = session.get('full_image_original_filename')  # Get the current photo filename from the session
    full_image_original_filename_url = session.get('full_image_original_filename_url')
    preview_image_filename_url = session.get('preview_image_filename_url')
    full_image_ai_filename_url = session.get('full_image_ai_filename_url')
    full_image_ai_filename = session.get('full_image_ai_filename')  # Get the current photo filename from the session
    

    # Process of deleting the photo only for pending status (if the customer leaves the page without payment)
    current_photo_original = Photo.query.filter_by(filename=full_image_original_filename, status=PhotoStatus.PENDING).first()
    
    if current_photo_original:
        print(f"Current photo found: {current_photo_original.path}")
        db.session.delete(current_photo_original)  # Delete the photo from the database
        db.session.commit()
        
        # Remove the HD photo from the server if it exists
        if os.path.exists(full_image_original_filename_url):
            os.remove(full_image_original_filename_url)
            print(f"HD photo {full_image_original_filename_url} deleted from server.")
        
        # Remove the preview photo from the server if it exists
        if os.path.exists(preview_image_filename_url):
            os.remove(preview_image_filename_url)
            print(f"Preview photo {preview_image_filename_url} deleted from server.")
    
    # Process of deleting the AI photo only for pending status (if the customer leaves the page without payment)
    current_photo_ai = Photo.query.filter_by(filename=full_image_ai_filename, status=PhotoStatus.PENDING).first()
    
    if current_photo_ai:
        print(f"Current AI photo found: {current_photo_ai.path}")
        db.session.delete(current_photo_ai)
        db.session.commit()
        
        # Remove the AI photo from the server if it exists
        if os.path.exists(full_image_ai_filename_url):
            os.remove(full_image_ai_filename_url)
            print(f"AI photo {full_image_ai_filename_url} deleted from server.")
    
    # Clear the session data
    clear_session()
    print("Exiting the application and clearing session data..")
    
    # Redirect to the index page
    return redirect(url_for('main.index'))

# Testing page (Only for development purposes)
@bp.route('/test')
def test():
    return render_template('test.html', index=False)
