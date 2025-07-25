const retakeButton = document.getElementById('retakeButton');
const stopButton = document.getElementById('stopButton');
const video = document.getElementById('video');
const countdownEl = document.getElementById("countdown");
const photo = document.getElementById("photo");
const canvas = document.getElementById("canvas");
const uploadButton = document.getElementById('uploadButton');
const startButton = document.getElementById('startButton');
const loadingButton = document.getElementById('loadingButton');
const settings = document.getElementById("photo-settings")
//const saveButton = document.getElementById("saveButton")
const countdownButton = document.getElementById("countdownButton");
const payButton = document.getElementById("payButton");
//const generateQRButton = document.getElementById("generateQRCode");
const beepSound = document.getElementById("beep-sound");
const paymentButton = document.getElementById("paymentButton");

document.addEventListener("DOMContentLoaded", function() {
    const exitButton = document.getElementById('exitButton');

    if (exitButton) {
        exitButton.addEventListener("click", (e) => {
            e.preventDefault();
            showConfirmationMessage("Exit", "Are you sure you want to exit ?", "Exit", "Cancel", "/exit");
        });
    }

    const width = window.innerWidth;
    const height = window.innerHeight;

    console.log(`Viewport size: ${width}x${height}`);
    
    // Camera will not turn on if the video element is not present
    if (!video) return;

    // Auto-load camera when the page loads
    // Request access to the user's camera
    const photoWidth = parseInt(settings.dataset.photoWidth);
    const photoHeight = parseInt(settings.dataset.photoHeight);
    console.log("Photo dimensions from Flask:", photoWidth, photoHeight);
    navigator.mediaDevices.getUserMedia({ 
        video: {
            width: { ideal: photoWidth },
            height: { ideal: photoHeight }
        },
        audio: false
    })
    .then(stream => {
        video.srcObject = stream;
    })
    .catch(error => {
        console.error('Error accessing the camera: ', error);
    });

    retakeButton.addEventListener('click', function() {
        console.log("Starting camera...");

        // Reset the photo element
        document.getElementById("photo").src = "";
        document.getElementById("photo").style.display = "none";
        retakeButton.style.display = "none";
        captureButton.style.display = "inline-block";
        captureButton.disabled = false;
        paymentButton.style.display = "none"
        //uploadButton.style.display = "none";
        //saveButton.style.display = "none";

        // Request access to the user's camera
        navigator.mediaDevices.getUserMedia({ 
            video: {
                width: { ideal: photoWidth },
                height: { ideal: photoHeight }
            },
            audio: false
        })
        .then(stream => {
            video.srcObject = stream;
        })
        .catch(error => {
            console.error('Error accessing the camera: ', error);
        });
    });

    startButton.addEventListener('click', function() {
        console.log("Starting camera...");
        // Request access to the user's camera
        navigator.mediaDevices.getUserMedia({ 
            video: {
                width: { ideal: photoWidth },
                height: { ideal: photoHeight }
                },
                audio: false
            })
            .then(stream => {
                video.srcObject = stream;
            })
            .catch(error => {
                console.error('Error accessing the camera: ', error);
            });
        });
    

    stopButton.addEventListener('click', function() {
        console.log("Stopping camera...");
        // Stop all video tracks
        if (video.srcObject) {
            const tracks = video.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            video.srcObject = null;
        } else {
            showAlertMessage("Camera already stopped!");
        }
    });

    `loadingButton.addEventListener('click', function() {
        showLoading();
        console.log("Loading screen shown...");
        setTimeout(() => {
            console.log("Hiding loading screen...");
            hideLoading();
        }, 5000); // Hide loading after 5 seconds
    })`

    uploadButton.addEventListener('click', function() {
        console.log("Uploading image...");
        showLoading("Generating image, please wait...");
        const imageData = canvas.toDataURL("image/png");

        console.log("Image data:", imageData);

        // Send the image data to the server
        fetch('/upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                image: imageData,
                background_filename: "Terengganu_Drawbridge.png" 
            }),
        })
        .then(response => response.json())
        .then(data => {
            console.log('Image uploaded successfully:', data);
            photo.src = data.image_url; 
            photo.style.display = "block";
            payButton.style.display = "inline-block";
            
        })
        .catch(error => {
            showAlertMessage("Failed to upload image. Please try again.");
            console.error('Error uploading image:', error);
            }
        ).finally(() => {
            showSuccessMessage("Image Generated", "Your image has been generated successfully!");
            hideLoading();  
        })
    });
        

    captureButton.addEventListener('click', function() {
        // Check if camera is turn on
        if (!video.srcObject) {
            showAlertMessage("Camera is not turned on. Please turn on the camera first.");
            return;
        }
        let count = 5;

        const countdownInterval = setInterval(() => {
            countdownEl.textContent = count;
            countdownEl.classList.remove("fade-in-out"); // reset animation
            void countdownEl.offsetWidth; // trigger reflow
            countdownEl.classList.add("fade-in-out");
            beepSound.currentTime = 0;
            beepSound.play().catch(e => console.warn("Beep failed:", e));
            countdownEl.classList.remove("hidden");
            countdownEl.classList.add("scale");
            captureButton.disabled = true;

            if (count === 0) {
              clearInterval(countdownInterval);
              countdownEl.classList.add("hidden");
              //beepSound.pause();
              beepSound.pause() // reset sound
              beepSound.currentTime = 0;
              // Capture image
              const context = canvas.getContext("2d");
              canvas.width = video.videoWidth;
              canvas.height = video.videoHeight;
              context.drawImage(video, 0, 0);
              photo.src = canvas.toDataURL("image/jpeg");
              photo.style.display = "block";
              retakeButton.style.display = "inline-block";
              uploadButton.style.display = "inline-block";
              captureButton.style.display = "none";
              paymentButton.style.display = "inline-block";
              //payButton.style.display = "inline-block";
              //saveButton.style.display = "inline-block"

            // Stop the video stream
            if (video.srcObject) {
                const tracks = video.srcObject.getTracks();
                tracks.forEach(track => track.stop());
                video.srcObject = null;
            }  
            }
        
            count--;
          }, 1000);
    });

    `saveButton.addEventListener('click', function() {
        // Save the image to the server
        fetch('/save_image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image: JSON.stringify({ image_url: photo.src })
                })
            })
            .then(res => res.json())
            .then(data => {
                console.log('Image saved successfully:', data);
                showSuccessMessage("Photo Saved", "Your image has been saved successfully!");
            })
            .catch(error => {
                console.error('Error:', error);
            });
          
    });`

    countdownButton.addEventListener('click', function() {
        console.log("Starting countdown...");
        let count = 5;
        const countdownInterval = setInterval(() => {
            countdownEl.textContent = count;
            countdownEl.classList.remove("fade-in-out"); // reset animation
            void countdownEl.offsetWidth; // trigger reflow
            countdownEl.classList.add("fade-in-out");
            beepSound.currentTime = 0;
            beepSound.play().catch(e => console.warn("Beep failed:", e));
            countdownEl.classList.remove("hidden");
            countdownEl.classList.add("scale");
            countdownButton.disabled = true;
            if (count === 0) {
                clearInterval(countdownInterval);
                beepSound.pause() // reset sound
                beepSound.currentTime = 0;
                countdownEl.classList.add("hidden");
                countdownButton.disabled = false;
            }
            count--;
        }, 1000);
    });

    paymentButton.addEventListener('click', function() {
        console.log("Redirecting to payment summary page...");
        fetch('/payment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image: photo.src
            })
        })
        .then(res => {
            if (res.redirected) {
              window.location.href = res.url; // ✅ Go to /payment page
            } else {
              // Optional: handle JSON if backend returns JSON
              return res.json();
            }
          }).catch(err => {
            console.error("Fetch error:", err);
          });
    });

    `generateQRButton.addEventListener('click', function() {
        fetch('/generate_qr_code')
        .then(response => response.json())
        .then(data => {
            console.log("Checking qr code ... ");
            console.log("Qr code link: " + data);
            showSuccessMessage("Qr code has been generated !")
        })
    });`
});

payButton.addEventListener('click', function() {
    console.log("Starting payment process...")
    showLoading("Processing your payment...");
    setTimeout(() => {
        fetch('/pay', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
        })
        .then(response => response.json())
        .then(data => {
            console.log("Test Payment Response:", data);
            if (data.redirect_url) {
                window.location.href = data.redirect_url;
            }
            else {
                showAlertMessage("Payment failed. Please try again.");
                hideLoading();
            }
        })
    }, 1000);
});


document.querySelectorAll(".frame-button").forEach(button => {
    button.addEventListener("click", function() {
        // Uncheck all buttons
        document.querySelectorAll(".frame-button").forEach(b => b.classList.remove("checked"));

        // Check clicked button
        this.classList.add("checked");
    })
});


document.querySelectorAll(".frame-button").forEach(btn => {
    btn.addEventListener('touchstart', () => {
        btn.style.transform = 'scale(0.95)';
    });
        btn.addEventListener('touchend', () => {
        btn.style.transform = 'scale(1)';
    });
        btn.addEventListener('mousedown', () => {
        btn.style.transform = 'scale(0.95)';
    });
        btn.addEventListener('mouseup', () => {
        btn.style.transform = 'scale(1)';
    });
});

function showLoading(text) {
    document.getElementById("loading-element").style.display = "block";
    document.getElementById("loading-text").style.display = "block";
    document.getElementById("blur-overlay").style.display = "block";
    document.getElementById("loading-text").textContent = text || "Loading, please wait...";
}

function hideLoading() {
    document.getElementById("loading-element").style.display = "none";
    document.getElementById("loading-text").style.display = "none";
    document.getElementById("blur-overlay").style.display = "none";
}

function showAlertMessage(message) {
    Swal.fire({
        icon: "error",
        title: "Error",
        text: message,
        scrollbarPadding: false,  
    });
}
function showSuccessMessage(title,message) {
    Swal.fire({
        icon: "success",
        title: title,
        text: message,
    });
}

function showConfirmationMessage(title, message, confirmMessage, cancelMessage, linkYes) {
    Swal.fire({
        title: title,
        text: message,
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: confirmMessage,
        cancelButtonText: cancelMessage,
      })
      .then((result) => {
        if (result.isConfirmed) {
            // User clicked confirm button
            window.location.href = linkYes; // Redirect to home page
        } 
    });
};

window.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes("/fail?")) {
      showConfirmationMessage("Payment Failed", "Your payment has failed. Please try again.", "Try Again", "/preview")
    }
});

