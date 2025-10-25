import enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum

db = SQLAlchemy()

class PhotoStatus(enum.Enum):
    PENDING = "pending"
    CANCELED = "canceled"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    REFUNDED = "refunded"

class PhotoType(enum.Enum):
    ORIGINAL = "original"
    AI = "ai"

class Photo(db.Model):
    __tablename__ = "photo"
    id   = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    type = db.Column(Enum(PhotoType, name="photo_type_enum"), nullable=False, default=PhotoType.ORIGINAL)
    frame = db.Column(db.String(50), nullable=False)
    path = db.Column(db.String(512), nullable=False)
    unique_code = db.Column(db.String(32), unique=True, nullable=False)
    date_of_save = db.Column(db.DateTime, nullable=False)
    status = db.Column(Enum(PhotoStatus, name="photo_status_enum"), nullable=False, default=PhotoStatus.PENDING)

class Payment(db.Model):
    __tablename__ = "payment"
    id   = db.Column(db.Integer, primary_key=True)
    payment_request_id = db.Column(db.String(50), unique=True, nullable=False)
    payment_id = db.Column(db.String(50), unique=True, nullable=True) 
    reference_id = db.Column(db.String(50), nullable=False, unique=True)
    status   = db.Column(db.String(20), nullable=False)
    frame = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    
