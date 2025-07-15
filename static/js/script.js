document.addEventListener("DOMContentLoaded", function() {
    const video = document.getElementById('video');
    const retakeButton = document.getElementById('retakeButton');
    //const stopButton = document.getElementById('stopButton');
    const countdownEl = document.getElementById("countdown");
    const photo = document.getElementById("photo");
    const canvas = document.getElementById("canvas");

    // Camera will not turn on if the video element is not present
    if (!video) return;

    // Auto-load camera when the page loads
    // Request access to the user's camera
    navigator.mediaDevices.getUserMedia({ video: true })
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

        // Request access to the user's camera
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                video.srcObject = stream;
            })
            .catch(error => {
                console.error('Error accessing the camera: ', error);
            });
    });

    `stopButton.addEventListener('click', function() {
        console.log("Stopping camera...");
        // Stop all video tracks
        if (video.srcObject) {
            const tracks = video.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            video.srcObject = null;
        }
    });`

    captureButton.addEventListener('click', function() {
        let count = 5;

        const countdownInterval = setInterval(() => {
            countdownEl.textContent = count;
            countdownEl.classList.remove("hidden");
            countdownEl.classList.remove("scale"); // reset animation
            void countdownEl.offsetWidth; // trigger reflow
            countdownEl.classList.add("scale");
        
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
              captureButton.style.display = "none";

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

});

document.querySelectorAll(".frame-button").forEach(button => {
    button.addEventListener("click", function() {
        // Uncheck all buttons
        document.querySelectorAll(".frame-button").forEach(b => b.classList.remove("checked"));

        // Check clicked button
        this.classList.add("checked");
    })
});
