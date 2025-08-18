from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash, jsonify
from utils import get_secure_image_url
from models import Photo, PhotoStatus

# routes/admin.py

bp = Blueprint("admin", __name__)

@bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin login route to authenticate the admin user.

    Returns:
        Response: Rendered HTML template for the admin login page or \
        redirects to admin download page upon successful login.
    """
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = request.form.get("password") or ""
        remember = request.form.get("remember") == "1"
        ok = (u == current_app.config["ADMIN_USERNAME"] and \
              p == current_app.config["ADMIN_PASSWORD"])
        ok = (u == current_app.config["ADMIN_USERNAME"] and p == current_app.config["ADMIN_PASSWORD"])

        if ok:
            session["is_admin"] = True
            if remember:
                session.permanent = True  # respect PERMANENT_SESSION_LIFETIME
            return redirect(url_for("admin.admin_download"))
        flash("Invalid credentials", "danger")
    return render_template("admin_login.html")

# Admin logout route
@bp.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin.admin_login"))

@bp.route('/admin/download', methods=['GET'])
def admin_download():
    """Render the admin page with payment status store (ADMIN ONLY).

    Returns:
        Response: Rendered HTML template for the admin page with payment status store.
    """
    if session.get("is_admin") != True:
        return redirect(url_for("admin.admin_login"))
    
    return render_template('admin_download.html', index=False)

@bp.route('/download', methods=['POST'])
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