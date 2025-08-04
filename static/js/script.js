document.documentElement.requestFullscreen();
selectedTimer = null; // Initialize selected timer

function setTimer(timer) {
    selectedTimer = timer;
    console.log("Selected timer:", selectedTimer);
    const timerDropdown = document.getElementById('timerDropdown');
    timerDropdown.classList.add('hidden');
}

// Function to toggle the dropdown visibility
function toggleTimerDropdown() {
    const timerDropdown = document.getElementById('timerDropdown');
    timerDropdown.classList.toggle('hidden');
}

// Show loading screen
function showLoading(text) {
    document.getElementById("loading-element").style.display = "block";
    document.getElementById("loading-text").style.display = "block";
    document.getElementById("blur-overlay").style.display = "block";
    document.getElementById("loading-text").textContent = text || "Loading, please wait";
}

// Hide loading screen
function hideLoading() {
    document.getElementById("loading-element").style.display = "none";
    document.getElementById("loading-text").style.display = "none";
    document.getElementById("blur-overlay").style.display = "none";
}

// Show alert message using SweetAlert2
function showAlertMessage(message) {
    Swal.fire({
        icon: "error",
        title: "Error",
        text: message,
        scrollbarPadding: false,  
    });
}

// Show success message using SweetAlert2
function showSuccessMessage(title,message) {
    Swal.fire({
        icon: "success",
        title: title,
        text: message,
    });
}

// Show confirmation message using SweetAlert2
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

// Start the camera with specified photo dimensions
async function startCamera(photoWidth, photoHeight) {
    try{
        showLoading();

        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: {
                width: { ideal: photoWidth },
                height: { ideal: photoHeight }
            },
            audio: false
        });
        const video = document.getElementById('video');
        video.srcObject = stream;
        video.onloadedmetadata = () => {
            video.play();
            hideLoading();
            };
    } catch (error) {
        console.error('Error accessing the camera: ', error);
        hideLoading();
        showAlertMessage("Failed to access camera. Please check your camera settings or permissions.");
    }
}

// Function to handle preview page buttons and camera functionality
function previewPageButtons(photoWidth, photoHeight) {
    const retakeButton = document.getElementById('retakeButton');
    const stopButton = document.getElementById('stopButton');
    const uploadButton = document.getElementById('uploadButton');
    const startButton = document.getElementById('startButton');
    const countdownButton = document.getElementById("countdownButton");
    const payButton = document.getElementById("payButton");
    const beepSound = document.getElementById("beep-sound");
    const paymentButton = document.getElementById("paymentButton");
    const video = document.getElementById('video');
    const countdownEl = document.getElementById("countdown");
    const photo = document.getElementById("photo");
    const canvas = document.getElementById("canvas");
    const timerButton = document.getElementById("timerButton");
    
    if (captureButton) {
        captureButton.addEventListener('click', function() {
            const previewButtonsContainer = document.getElementById("container-button-bottom")
            console.log("Capture button clicked...");
            // Check if camera is turn on
            if (!video.srcObject) {
                showAlertMessage("Camera is not turned on. Please turn on the camera first.");
                return;
            }
            previewButtonsContainer.classList.toggle("hiddenFade");
            setTimeout(() => {
                previewButtonsContainer.style.display = "none";
            }, 500); // must match the transition duration (800ms)
            
            // Initialize countdown
            let count = 0  
            
            if (selectedTimer == null) {  
                count = 5;              // Default to 5 seconds if no timer is selected  
            } else {
                count = selectedTimer // Use the selected timer value
            }
            
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
                captureButton.disabled = true;
                timerButton.disabled = true;

                if (count === 0) {
                  clearInterval(countdownInterval);
                  countdownEl.classList.add("hidden");
                  previewButtonsContainer.style.display = "flex"; 

                  // Force reflow to ensure transition triggers
                  void previewButtonsContainer.offsetWidth;
                  previewButtonsContainer.classList.toggle("hiddenFade");
                  beepSound.pause() 
                  beepSound.currentTime = 0;   // reset sound

                  // Capture image
                  const context = canvas.getContext("2d");
                  canvas.width = video.videoWidth;
                  canvas.height = video.videoHeight;
                  context.drawImage(video, 0, 0);
                  photo.src = canvas.toDataURL("image/jpeg");
                  photo.style.display = "block";
                  video.style.display = "none";

                  // Photo buttons
                  retakeButton.style.display = "inline-block";
                  uploadButton.style.display = "inline-block";
                  captureButton.style.display = "none";
                  paymentButton.style.display = "inline-block";
                  timerButton.style.display = "none";
                  //document.getElementById("uploadButton").click();
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
    }

    // Change timer for the coundown timer
    if (timerButton) {
        timerButton.addEventListener('click', function() {
            console.log("Changing timer...");

        })
    }

    if (retakeButton) {
        retakeButton.addEventListener('click', function() {
            console.log("Starting camera...");
    
            // Reset the photo element
            document.getElementById("photo").src = "";
            document.getElementById("photo").style.display = "none";
            document.getElementById("video").style.display = "block";
            retakeButton.style.display = "none";
            captureButton.style.display = "inline-block";
            paymentButton.style.display = "none"
            captureButton.disabled = false;
            uploadButton.style.display = "none";
            timerButton.style.display = "inline-block";
            timerButton.disabled = false;
            //saveButton.style.display = "none";
    
            // Request access to the user's camera
            startCamera(photoWidth, photoHeight);
        });
    }

    if (uploadButton) {
        uploadButton.addEventListener('click', function() {
            console.log("Uploading image...");
            showLoading("Generating image, please wait...");
            setTimeout( function() {
                document.getElementById("loading-text").textContent = "This might take a while, please wait...";
            }, 15000)
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
                
            })
            .catch(error => {
                showAlertMessage("Failed to upload image. Please try again.");
                console.error('Error uploading image:', error);
                }
            ).finally(() => {
                hideLoading();  
            })
        });
    }

    if (paymentButton) {
        paymentButton.addEventListener('click', function() {
            console.log("Redirecting to payment summary page...");
            showLoading();
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
    }

    if (startButton) {
        startButton.addEventListener('click', function() {
            console.log("Starting camera...");
            // Request access to the user's camera
            startCamera(photoWidth, photoHeight);
        });
    }

    if (stopButton) {
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
    }

    if (countdownButton) {
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
    }

    loadingButton.addEventListener('click', function() {
        showLoading();
        console.log("Loading screen shown...");
        setTimeout(() => {
            console.log("Hiding loading screen...");
           hideLoading();
        }, 5000); // Hide loading after 5 seconds
    });
        

    //saveButton.addEventListener('click', function() {
        // Save the image to the server
    //    fetch('/save_image', {
    //        method: 'POST',
    //        headers: {
    //           'Content-Type': 'application/json'
    //      },
    //        body: JSON.stringify({
    //            image: JSON.stringify({ image_url: photo.src })
    //            })
    //       })
    //        .then(res => res.json())
    //        .then(data => {
    //            console.log('Image saved successfully:', data);
    //           showSuccessMessage("Photo Saved", "Your image has been saved successfully!");
    //        })
    //        .catch(error => {
    //            console.error('Error:', error);
    //        });    
    //});

    //generateQRButton.addEventListener('click', function() {
    //    fetch('/generate_qr_code')
    //    .then(response => response.json())
    //    .then(data => {
    //        console.log("Checking qr code ... ");
    //        console.log("Qr code link: " + data);
    //        showSuccessMessage("Qr code has been generated !")
    //    })
    //});
};  

//const loadingButton = document.getElementById('loadingButton');
const settings = document.getElementById("photo-settings")
//const saveButton = document.getElementById("saveButton")
const payButton = document.getElementById("payButton");
//const generateQRButton = document.getElementById("generateQRCode");


document.addEventListener("DOMContentLoaded", function() {
    const path = window.location.pathname;
    const exitButton = document.getElementById('exitButton');
    console.log("Path:", window.location.pathname);
      
    // Exit button needs to load first.
    if (exitButton) {
        exitButton.addEventListener("click", (e) => {
            e.preventDefault();
            showConfirmationMessage("Exit", "Are you sure you want to exit ?", "Exit", "Cancel", "/exit");
        });
    }
    
    if (path === ("/fail")) {
        showConfirmationMessage("Payment Failed", "Your payment has failed. Please try again.", "Try Again", "Return Home", "/preview")
    }
    
    if (path === ("/preview")) {
        // Get the video element
        const width = window.innerWidth;
        const height = window.innerHeight;
        document.getElementById('timerButton').addEventListener('click', toggleTimerDropdown);
        
        // DEBUG: Viewport size
        console.log(`Viewport size: ${width}x${height}`);

        // Get the video element
        const photoWidth = parseInt(settings.dataset.photoWidth);
        const photoHeight = parseInt(settings.dataset.photoHeight);

        // Request access to the user's camera
        // Camera auto-load on preview page
        console.log("Photo dimensions from Flask:", photoWidth, photoHeight);

        window.onload = function() {
            // Start the camera
            startCamera(photoWidth, photoHeight);

            // Show all the page buttons
            previewPageButtons(photoWidth, photoHeight);
            setTimeout(() => {
                const content = document.getElementById("content");
                content.style.display = 'block';
            }, 500);
        }
        
        // This needs to be in preview if statement
        if (path === "/payment-summary"){
            //const photoFilename = {{ photo_filename }};
            window.onload = function() {
                const photoSummary = document.getElementById("photo-summary");
                const canvasSummary = document.getElementById("canvas-summary");
                photoSummary.src = "/static/{{ photo_filename }}";
                photoSummary.style.display = "block";
                setTimeout(() => {
                    hideLoading();
                    content.style.display = 'block';
                }, 500);

            }
        }
    };    
    
});

document.querySelectorAll(".frame-button").forEach(button => {
    button.addEventListener("click", function() {
        // Uncheck all buttons
        document.querySelectorAll(".frame-button").forEach(b => b.classList.remove("checked"));

        // Check clicked button
        this.classList.add("checked");
    })
});

if (payButton) {
    payButton.addEventListener('click', function() {
        console.log("Starting payment process...")
        showLoading("Processing your payment...");
        setTimeout(() => {
            fetch('/pay', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
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
    
}


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


