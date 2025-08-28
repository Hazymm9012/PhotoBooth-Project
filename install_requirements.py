import sys
import subprocess

req_file = "/home/tns/PhotoBooth-Project/requirements.txt"

print("Using Python:", sys.executable)
try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
    print("✅ Requirements installed successfully.")
except subprocess.CalledProcessError as e:
    print("❌ Error installing requirements:", e)