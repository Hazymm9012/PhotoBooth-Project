document.addEventListener("DOMContentLoaded", function() {
    const video = document.getElementById('video');
    const retakeButton = document.getElementById('retakeButton');
    const stopButton = document.getElementById('stopButton');
    const countdownEl = document.getElementById("countdown");
    const photo = document.getElementById("photo");
    const canvas = document.getElementById("canvas");
    const uploadButton = document.getElementById('uploadButton');
    const startButton = document.getElementById('startButton');
    const loadingButton = document.getElementById('loadingButton');
    const settings = document.getElementById("photo-settings")
    const saveButton = document.getElementById("saveButton")
    
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
        uploadButton.style.display = "none";
        saveButton.style.display = "none";

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
            alert("Camera already stopped.")
        }
    });

    loadingButton.addEventListener('click', function() {
        showLoading();
        console.log("Loading screen shown...");
        setTimeout(() => {
            console.log("Hiding loading screen...");
            hideLoading();
        }, 5000); // Hide loading after 5 seconds
    })

    uploadButton.addEventListener('click', function() {
        console.log("Uploading image...");
        showLoading();
        const imageData = canvas.toDataURL("image/jpeg");

        console.log("Image data:", imageData);

        // Send the image data to the server
        fetch('/upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                image: imageData,
                background_filename: "Terengganu_Drawbridge.jpg" 
            }),
        })
        .then(response => response.json())
        .then(data => {
            console.log('Image uploaded successfully:', data);
            photo.src = data.image_url; 
            photo.style.display = "block";
            
        })
        .catch(error => {
            alert('Error uploading image. Please try again.');
            console.error('Error uploading image:', error);
            }
        ).finally(() => {
            hideLoading();  
        })
    });
        

    captureButton.addEventListener('click', function() {
        // Check if camera is turn on
        if (!video.srcObject) {
            alert("Please turn on the camera first.");
            return;
        }
        let count = 5;

        const countdownInterval = setInterval(() => {
            countdownEl.textContent = count;
            countdownEl.classList.remove("hidden");
            countdownEl.classList.remove("scale"); // reset animation
            void countdownEl.offsetWidth; // trigger reflow
            countdownEl.classList.add("scale");
            captureButton.disabled = true;
        
            if (count === 0) {
              clearInterval(countdownInterval);
              countdownEl.classList.add("hidden");
        
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
              saveButton.style.display = "inline-block"

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

    saveButton.addEventListener('click', function() {
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
                alert("Photo has been successfully saved.")
            })
            .catch(error => {
                console.error('Error:', error);
            });
          
    });

});

document.querySelectorAll(".frame-button").forEach(button => {
    button.addEventListener("click", function() {
        // Uncheck all buttons
        document.querySelectorAll(".frame-button").forEach(b => b.classList.remove("checked"));

        // Check clicked button
        this.classList.add("checked");
    })
});

function showLoading() {
    document.getElementById("loading-element").style.display = "block";
    document.getElementById("loading-text").style.display = "block";
    document.getElementById("blur-overlay").style.display = "block";
}

function hideLoading() {
    document.getElementById("loading-element").style.display = "none";
    document.getElementById("loading-text").style.display = "none";
    document.getElementById("blur-overlay").style.display = "none";
}
