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

def save_status(payment_id, status):
    with lock:
        payment_status_store[payment_id] = status
        with open(FILE_PATH, 'w') as f:
            json.dump(payment_status_store, f)

def get_status(payment_id):
    return payment_status_store.get(payment_id)
