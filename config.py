# config.py
import os
from openai import OpenAI
from dotenv import load_dotenv
from flask import request

# Load environment variables from .env file
load_dotenv()

class Config:
    # Secret Key for session management
    SECRET_KEY = os.getenv("SECRET_KEY")
    
    # DB configuration
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Environment variables (these should be set in env)
    BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000/')      # Base URL for the app
    HITPAY_SALT = os.getenv('HITPAY_SALT')
    HITPAY_API_KEY = os.getenv('HITPAY_API_KEY')
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')  
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD') 
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') 
    
    # Allowed IPs to access the app (Configure IP Address based on location)
    ALLOWED_IPS = ['202.168.65.122', '127.0.0.1']

    # Constants and global variables
    PHOTO_DIR = 'full_photos'
    PREVIEW_DIR = 'static/preview_photos'
    
    # Hitpay links
    HITPAY_URL = "https://api.sandbox.hit-pay.com/v1/payment-requests"
    
    # OpenAI client configuration
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=80)
    
class devConfig(Config):
    DEBUG = True
    TESTING = True
    SESSION_COOKIE_SECURE = False 
    SESSION_COOKIE_SAMESITE = "Lax"
    
class prodConfig(Config):
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"  # or "None" if you need cross-site