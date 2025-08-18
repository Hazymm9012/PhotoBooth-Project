from flask import Flask
from routes.main import bp as main_bp
from extensions import db, migrate
from config import Config
from models import *
    

def create_app(config_class=Config):
    """
    Create and configure the Flask application.
    :param config_class: Configuration class to use for the app
    :return: Configured Flask app instance
    """
    # Create Flask application instance
    app = Flask(__name__)
    
    # Load configuration from Config class
    app.config.from_object(config_class)  
    app.config["OPENAI_CLIENT"] = Config.client # Set OpenAI client in app config
    db.init_app(app)                            # Initialize SQLAlchemy with the app
    migrate.init_app(app, db)                   # Initialize Flask-Migrate with the app
    
    # Create database tables if they do not exist
    with app.app_context():
        db.create_all()                         # Create database tables if they do not exist
        print("Models mapped:", list(db.metadata.tables.keys()))
    
    # Register main blueprint        
    app.register_blueprint(main_bp)
    
    return app

