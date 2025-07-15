document.addEventListener("DOMContentLoaded", function() {
    const video = document.getElementById('video');
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');

    startButton.addEventListener('click', function() {
        console.log("Starting camera...");
        // Request access to the user's camera
        navigator.mediaDevices.getUserMedia({ video: true })
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
        }
    });

});
