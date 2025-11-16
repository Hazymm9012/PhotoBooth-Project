# PhotoBooth Kiosk Web App

A kiosk-style **PhotoBooth web application** built with **Python (Flask)** that allows users to:

- Capture their photo and convert it into AI-Generated photo
- Preview their pixar-style AI-generated image with Terengganu Drawbridge as the background.
- Pay securely via **Hitpay**.
- Download their image to their phone using QR Code
- Print their image using **Admin System**.

Designed to run in a kiosk environment with a touch-friendly UI.

---
## Features

- 📸 **Photo Capture**  
    - Capture your photo from a connected camera.

- 🤖 **AI-Powered Image Generation**  
    - ChatGPT API Integration
    - Generate a pixar-style image from the captured photo

- 💳 **Secure Payments (HitPay)**  
    - Hitpay Checkout Integration
    - Webhook handling
    - Signature verification for payment integrity

- 📂 **Download Image via QR Code**
    - Download the purchased image to the user's phone by scanning the provided QR Code

- 📂 **Print Image via Admin Panel**
    - Present the 6-digit code provided after payment successful page to the counter for printing purpose.

- 🖥️ **Kiosk-Friendly UI** 
    - Simple, large-button interface designed for use at the kiosk

---
## Tech Stack

**Backend**

- Python
- Flask
- Hitpay API (payments)
- Webhooks + HMAC signature verification
- MySQL for Database

**Frontend** 
- HTML, CSS & JavaScript
- Touch-friendly layout for kiosk devices

**Infrastructure & Tools**

- Tested on Windows, Linux and MacOS
- Environment variables for secrets 
- Git for version control

---
## Project Structure
```text
photobooth-project/
  routes/                       # Backend Functions
    admin.py                    # Admin backend
    error.py                    # Error backend
    main.py                     # Main backend
    payment.py                  # Payment backend
    photo.py                    # Photo backend
  static/                       # Static Assets 
    audio/                      # Store sound effect
    css/                        # CSS configuration
    images/                     # Store static images for the app    
    preview_photos/             # Store low quality AI-generated image(temporary)
    js/                         # JavaScript             
  templates/                    # HTML templates
    403.html
    404.html
    500.html
    admin_download.html
    admin_login.html
    base.html
    check_status.html
    chooseSize.html
    error.html
    fail.html
    index.html
    payment.html
    preview.html
    redirect.html
    success.html
  docs/                        # Screenshots for README.md
    Checkout-Image.png 
    Home Page-Image.png
    Preview-Image.png
    Success-Image.png
  full_AI_Photos/             # Store all AI-generated Photos
  full_original_photos/       # Store all Original Photos
  .gitignore
  README.md
  requirements.txt            # A list of dependencies required
  app.py                      # Flask App Configuration and Blueprints
  config.py                   # Configuration Settings
  extensions.py               # Database extensions   
  models.py                   # Database models
  run.py                      # Run the app 
  utils.py                    # Helper functions
```

---
## Screenshots

### Home Screen
![Home Screen](docs/Home%20Page-Image.png)

### Preview Page
![Preview Page](docs/Preview-Image.png)

### Checkout Page
![Checkout Page](docs/Checkout-Image.png)

### Success Page
![Success Page](docs/Success-Image.png)

> **Note**: These screenshots are for demonstration only. The face is blurred for privacy purpose.
---

## Getting Started

### Step 1: Git clone from Repository
```bash
git clone https://github.com/Hazymm9012/PhotoBooth-Project.git
cd PhotoBooth-Project
```

### Step 2: Create Environment Variables
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```
### Step 3: Install dependencies
```bash
pip install -r requirement.txt
```

## Configuration
This Project uses environment variables for API keys and secrets. 

### Step 1: Copy `.env.example` to `.env`
```bash
cp .env.example .env
```

### Step 2: Fill the values in `.env` with your own values
```bash
# Example environment configuration file for the Flask web application.
BASE_URL=your_main_app_url_here

# API keys and secrets
HITPAY_API_KEY=your_hitpay_api_key_here
HITPAY_SALT=your_hitpay_salt_here
OPENAI_API_KEY=your_openai_api_key_here

# Security and database settings
SECRET_KEY=your_flask_secret_key_here
DATABASE_URL=your_database_url_here

# Admin credentials
ADMIN_USERNAME=your_admin_username_here
ADMIN_PASSWORD=your_admin_password_here

# Flask environment setting
FLASK_ENV=production
```

> **Example for Database URL**
> - mysql+pymysql://your_username:your_password@localhost/  photobooth?unix_socket=/tmp/mysql.sock&charset=utf8mb4
>  - Replace `your_username` and `your_paswword`with your own username and password
    
> **Notes:** These keys are not included for security purposes. Please provide your own API keys.

---
## How It Works (High Level)

### 1. User Interaction
- User lands on the home screen
- User chooses photo frame such as portrait or landscape size.
- User takes a photo and then using ChatGPT API, it generates the pixar-style image with Terengganu Drawbridge as the background.
- The app previews the image in low-quality image.
- User goes to checkout page for payment confirmation.
- User makes payment via Hitpay

### 2. Payment Flow
- The backend for the payment request is handled using Hitpay API.
- User is redirected to an embedded payment page.
- After payment, Hitpay redirects the user back to the redirection URL page for callback and sends a webhook to the backend.

### 3. Verification
- The backend verifies the HMAC signature from the Hitpay webhook using `HITPAY_SALT`
- After the verification is successful and complted payment, the app redirect to success page.
- If the payment unsuccessful or there is a problem with the payment integrity, the app redirects the user to failed page.

### 4. Image Generation
- The app generates the AI Image based on the captured photo and a preset photo of Terengganu Drawbridge. A prompt to generate the pixar-style image is also send to `ChatGPT API` for image generation
- The model used for image generation is `GPT-4o-mini` for faster generation.
- A link to AI-generated image is generated and merge into a `QR code`
- A `6-digit code` is generated which links to the AI-generated image.

### 5. Result
- The user lands at the `success` page.
- The page shows the generated `QR Code` to download the image using a phone's camera.
- The `6-digit code` can be given to the print counter to allow for printing purpose.

### 6. Database Information
- The database has two tables: `Payment` & `Photo`
- `Payment` is used to store payment information for payment verfication purpose. Payment status is updated using webhook. 
- `Photo` is used to store photos information for retrieval purpose using the QR code and 6-digit code.

---
## Limitations & Future Improvements
- Currently requires valid API keys (HitPay and optional AI image API) to run end-to-end.
- Could benefit from:
  - A full admin interface. Currently, the admin interface only allows downloading the image via the 6-digit code for printing purpose.
  - A full integrated printing system with printing interface. 
  - Automated tests to cover payment system and image pipelines.

---
## Contact
If you want to know more about this project:
- Author: Muhammad Hazim
- Email: github@hazim-tech.com
---

