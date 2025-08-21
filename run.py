from config import devConfig, prodConfig
from app import create_app
import os

# Determine the environment and create the Flask app accordingly
if os.environ.get("FLASK_ENV") == "production":
    app = create_app(prodConfig)
else:
    app = create_app(devConfig)
    
if __name__ == "__main__":
    app.run(debug=True, port=8000)
