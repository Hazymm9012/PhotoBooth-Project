from flask import Blueprint, render_template

bp = Blueprint("error", __name__)

@bp.app_errorhandler(403)
def forbidden_error(error):
    """Handle 403 Forbidden errors by rendering the 403 error page."""
    return render_template('403.html'), 403

@bp.app_errorhandler(404)
def not_found_error(error):
    """Handle 404 errors by rendering the 404 error page."""
    return render_template('404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server Errors by rendering the 500 error page."""
    return render_template('500.html'), 500