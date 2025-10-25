import time
import json
import os
from threading import Lock

FILE_PATH = 'payment_status_store.json'
lock = Lock()
payment_status_store = {}

def load_status_store():
    global payment_status_store
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'r') as f:
            payment_status_store = json.load(f)
    else:
        payment_status_store = {}

def save_status(payment_request_id, payment_id, status):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    with lock:
        payment_status_store[payment_request_id] = {
            'payment_id': payment_id,
            'status': status,
            'timestamp' : timestamp
        }
        with open(FILE_PATH, 'w') as f:
            json.dump(payment_status_store, f)

def get_status(payment_id):
    return payment_status_store.get(payment_id)

def get_last_item_from_store():
    with lock:
        if payment_status_store:
            last_key = list(payment_status_store.keys())[-1]
            return last_key
        return None
