import {
    retakeButton,
    stopButton,
    uploadButton,
    startButton,
    countdownButton,
    beepSound,
    paymentButton,
    video,
    bottomButtonsContainer,
    topButtonsContainer,
    countdownEl,
    photo,
    canvas,
    timerContainerButtons,
    settings,
    loadingButton,
    shutterSound
} from './dom.js';
import {
    showLoading,
    hideLoading,
    startCamera,
    showAlertMessage,
    toggleFlash,
    selectedTimer,
    showConfirmationMessage,
    fetchFullImageUrl
} from './utils.js';

// Function to handle preview page buttons and camera functionality
export function previewPageButtons(photoWidth, photoHeight) {
    // capture button functionality
    if (captureButton) {
        captureButton.addEventListener('click', function () {
            captureButtonHandler();
        });
    }

    // Retake button functionality
    if (retakeButton) {
        retakeButton.addEventListener('click', async function () {
            retakeButtonHandler();
        });
    }

    // Upload button functionality
    if (uploadButton) {
        uploadButton.addEventListener('click', function () {
            uploadButtonHandler();
        });
    }

    // Payment Summary button functionality
    if (paymentButton) {
        paymentButton.addEventListener('click', function () {
            paymentButtonHandler();
        });
    }

    // Start camera button functionality (DEBUG)
    if (startButton) {
        startButton.addEventListener('click', function () {
            startCameraHandler();
        });
    }

    // Stop camera button functionality (DEBUG)
    if (stopButton) {
        stopButton.addEventListener('click', function () {
            stopButtonHandler();
        });
    }

    // Countdown button functionality (DEBUG)
    if (countdownButton) {
        countdownButton.addEventListener('click', function () {
            countdownButtonHandler();
        });
    }

    // Trigger loading screen (DEBUG)
    if (loadingButton) {
        loadingButton.addEventListener('click', function () {
            loadingButtonHandler();
        });
    }
}

// Show or hide the password input field (Used in Admin Login Only)
export function togglePw() {
    const input = document.getElementById('password');
    const btn = event.currentTarget;
    const isPw = input.type === 'password';
    input.type = isPw ? 'text' : 'password';
    btn.setAttribute('aria-label', isPw ? 'Hide password' : 'Show password');
    btn.textContent = isPw ? '🙈' : '👁️';
}

window.togglePw = togglePw; // Expose togglePw function globally

/* Helper functions to handle button clicks and camera functionality 
    * These functions are used in the preview page to handle button clicks
    * and camera functionality except for payButtonHandler.
    * payButtonHandler will be called in script.js
*/

export let lastPhoto = null; // Variable to store the last photo taken

async function captureButtonHandler() {
    console.log('Capture button clicked...');

    // Call updateOldPhotoStatus function to remove the old photo status
    fetch('/update_old_photo_status', {
        method: 'POST',
    }).catch((error) => {
        console.error('Error updating old photo status:', error);
    });

    // Check if camera is turn on
    if (!video.srcObject) {
        showAlertMessage(
            'Camera is not turned on. Please turn on the camera first.',
        );
        return;
    }
    bottomButtonsContainer.classList.toggle('hiddenFade');
    topButtonsContainer.classList.toggle('hiddenFade');
    setTimeout(() => {
        bottomButtonsContainer.style.display = 'none';
        topButtonsContainer.style.display = 'none';
    }, 500); // must match the transition duration (800ms)

    // Initialize countdown
    let count = 0;

    if (selectedTimer == null) {
        count = 5;                  // Default to 5 seconds if no timeris selected
    } else {
        count = selectedTimer;      // Use the selected timer value
    }

    // Start countdown
    const countdownInterval = setInterval(async function () {
        countdownEl.textContent = count;
        countdownEl.classList.remove('fade-in-out'); // reset animation
        void countdownEl.offsetWidth; // trigger reflow
        countdownEl.classList.add('fade-in-out');
        beepSound.currentTime = 0;
        beepSound.play().catch((e) => console.warn('Beep failed:', e));
        countdownEl.classList.remove('hidden');
        countdownEl.classList.add('scale');
        countdownButton.disabled = true;
        captureButton.disabled = true;

        // If count reaches zero
        if (count === 0) {
            clearInterval(countdownInterval);       // Stop the countdown
            countdownEl.classList.add('hidden');    // Hide countdown element
            toggleFlash();                          // Toggle flash effect
            beepSound.pause();
            beepSound.currentTime = 0;              // reset sound
            shutterSound.currentTime = 0;           // reset sound

            // Play shutter sound
            shutterSound
                .play()
                .catch((e) => console.warn('Shutter sound failed:', e));

            // Capture image from camera and show it in the photo element
            const context = canvas.getContext('2d');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0);
            photo.src = canvas.toDataURL('image/jpeg');
            photo.style.display = 'block';
            video.style.display = 'none';

            // Save the full image URL to the server
            const oriRes = await fetch('/save_image/full', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ image: JSON.stringify({ image_url: photo.src }) }),
            });

            if (!oriRes.ok) {
                let msg = '';
                try {
                    const errBody = await oriRes.json();
                    msg = errBody?.error || JSON.stringify(errBody);
                } catch {
                    msg = oriRes.statusText;
                }
                throw new Error(`Save failed: ${msg || `HTTP ${oriRes.status}`}`);
            }
    
            const savedOri = await oriRes.json();
            if (!savedOri?.full_image_original_filename_url) {
                throw new Error('Save response missing full_image_original_filename_url');
            }
            console.log('Original Image saved successfully:', savedOri);

            // Save the image for preview (Only enable this if testing original image). For production, disable this
            const previewRes = await fetch('/save_image/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ image: JSON.stringify({ image_url: photo.src }) }),
            });

            if (!previewRes.ok) {
                let msg = '';
                try {
                    const errBody = await previewRes.json();
                    msg = errBody?.error || JSON.stringify(errBody);
                } catch {
                    msg = previewRes.statusText;
                }
                throw new Error(`Save failed: ${msg || `HTTP ${previewRes.status}`}`);
            }
    
            const savedPreview = await previewRes.json();
            if (!savedPreview?.preview_image_filename_url) {
                throw new Error('Save response missing preview_image_filename_url');
            }
            console.log('Preview Image saved successfully:', savedPreview);

            // Change buttons visibility
            retakeButton.style.display = 'inline-block';
            uploadButton.style.display = 'inline-block';
            captureButton.style.display = 'none';
            paymentButton.style.display = 'inline-block';
            timerContainerButtons.style.display = 'none';

            setTimeout(() => {
                bottomButtonsContainer.style.display = 'flex';
                topButtonsContainer.style.display = 'flex';
                bottomButtonsContainer.classList.toggle('hiddenFade');
                topButtonsContainer.classList.toggle('hiddenFade');
                void bottomButtonsContainer.offsetWidth;
                void topButtonsContainer.offsetWidth;
                //document.getElementById("uploadButton").click();  // Auto-upload function
            }, 1500);

            // Stop the video stream
            if (video.srcObject) {
                const tracks = video.srcObject.getTracks();
                tracks.forEach((track) => track.stop());
                video.srcObject = null;
            }
        }

        count--;
    }, 1000);
};

async function retakeButtonHandler() {
    console.log('Starting camera...');

    // Reset the photo and video elements
    photo.src = '';
    photo.style.display = 'none';
    video.style.display = 'block';

    // Retrieve photo dimensions from settings
    const photoWidth = parseInt(settings.dataset.photoWidth);
    const photoHeight = parseInt(settings.dataset.photoHeight);

    // Change buttons visibility
    retakeButton.style.display = 'none';
    captureButton.style.display = 'inline-block';
    paymentButton.style.display = 'none';
    captureButton.disabled = false;
    uploadButton.style.display = 'none';
    timerContainerButtons.style.display = 'inline-block';

    // Delete the previous photo from the server. Data acquired from Flask.
    await fetch('/delete_photo', {
        method: 'POST',
    });

    // Request access to the user's camera
    startCamera(photoWidth, photoHeight);
};

async function uploadButtonHandler() {
    console.log('Uploading image...');

    // Show loading screen
    showLoading('Generating image, please wait...');
    // Change the text afte r 15 seconds
    setTimeout(function () {
        document.getElementById('loading-text').textContent =
            'This might take a while, please wait...';
    }, 15000);

    // Check if the photo element has a valid image source
    let imageData = null;
    try {
        const fullImageUrl = await fetchFullImageUrl();
        console.log('Full image URL fetched:', fullImageUrl);
        if (!fullImageUrl) {
            throw new Error('Failed to fetch full image URL');
        }
        imageData = fullImageUrl;
        console.log('Image data captured:', imageData);

        const controller = new AbortController();
        const timeoutMs = 90000; // 90 seconds timeout
        const timer = setTimeout(() => controller.abort(), timeoutMs);

        let uploadRes;
        try {
            uploadRes = await fetch('/upload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image: imageData,
                    background_filename: 'Terengganu_Drawbridge.png',
                }),
                signal: controller.signal, // Attach the abort signal
            });
        } finally {
            clearTimeout(timer); // Clear the timeout if fetch completes
        }

        if (!uploadRes.ok) {
            // Handle error from upload API
            let serverMsg = '';
            try {
                const errBody = await uploadRes.json();
                serverMsg = errBody.error?.message || uploadRes.statusText;
            } catch {
                serverMsg = uploadRes.statusText;
            }
            throw new Error(`Upload failed: ${serverMsg || `HTTP ${uploadRes.status}`}`);
        }

        const uploadData = await uploadRes.json();
        if (!uploadData?.image_url) throw new Error('Upload response missing image_url');

        // Log the upload data
        console.log('Image uploaded successfully:', uploadData);
        document.getElementById('loading-text').textContent = 'Showing your image...';

        // Save the image URL to the server
        const saveRes = await fetch('/save_image/ai', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ image: JSON.stringify({ image_url: uploadData.image_url }) }),
        });

        if (!saveRes.ok) {
            let msg = '';
            try {
                const errBody = await saveRes.json();
                msg = errBody?.error || JSON.stringify(errBody);
            } catch {
                msg = saveRes.statusText;
            }
            throw new Error(`Save failed: ${msg || `HTTP ${saveRes.status}`}`);
        }

        const previewAiRes = await fetch('/save_image/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ image: JSON.stringify({ image_url: uploadData.image_url }) }),
        });

        if (!previewAiRes.ok) {
            let msg = '';
            try {
                const errBody = await previewAiRes.json();
                msg = errBody?.error || JSON.stringify(errBody);
            } catch {
                msg = previewAiRes.statusText;
            }
            throw new Error(`Save failed: ${msg || `HTTP ${previewAiRes.status}`}`);
        }

        const previewAiData = await previewAiRes.json();
        if (!previewAiData?.preview_image_filename_url) {
            throw new Error('Save response missing preview_image_filename_url');
        }
        console.log('Image saved successfully:', previewAiData);

        // Display the saved image in the photo element
        photo.addEventListener('load', () => {
            hideLoading();
            console.log('Image loaded successfully.');
        }, { once: true });

        photo.src = previewAiData.preview_image_filename_url;
        photo.style.display = 'block';
    } catch (error) {
        showAlertMessage('Error: ' + error.message);
        console.error('Upload flow error:', error);
        hideLoading();
    } finally {
        // Reset the buttons visibility
        // retakeButton.style.display = 'inline-block';
        // uploadButton.style.display = 'none';
        // captureButton.style.display = 'none';
        // paymentButton.style.display = 'inline-block';
        // countdownEl.classList.add('hidden');
        // countdownButton.disabled = false;
    }

}

function paymentButtonHandler() {
    console.log('Redirecting to payment summary page...');
    showLoading();
    fetch('/payment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            image: photo.src,
        }),
    })
        .then((res) => {
            if (res.redirected) {
                hideLoading();
                window.location.href = res.url; // ✅ Go to /payment page
            } else {
                return res.json();
            }
        })
        .catch((err) => {
            console.error('Fetch error:', err);
        });
}

function startCameraHandler() {
    console.log('Starting camera...');
    // Request access to the user's camera
    startCamera(photoWidth, photoHeight);
}

function stopButtonHandler() {
    console.log('Stopping camera...');
    // Stop all video tracks
    if (video.srcObject) {
        const tracks = video.srcObject.getTracks();
        tracks.forEach((track) => track.stop());
        video.srcObject = null;
    } else {
        showAlertMessage('Camera already stopped!');
    }
};

function countdownButtonHandler() {
    console.log('Starting countdown...');
    let count = 5;
    const countdownInterval = setInterval(() => {
        countdownEl.textContent = count;
        countdownEl.classList.remove('fade-in-out'); // reset animation
        void countdownEl.offsetWidth; // trigger reflow
        countdownEl.classList.add('fade-in-out');
        beepSound.currentTime = 0;
        beepSound.play().catch((e) => console.warn('Beep failed:', e));
        countdownEl.classList.remove('hidden');
        countdownEl.classList.add('scale');
        countdownButton.disabled = true;
        if (count === 0) {
            clearInterval(countdownInterval);
            beepSound.pause(); // reset sound
            beepSound.currentTime = 0;
            countdownEl.classList.add('hidden');
            countdownButton.disabled = false;
        }
        count--;
    }, 1000);
}

function loadingButtonHandler() {
    console.log('Loading screen shown...');
    showLoading();
    setTimeout(() => {
        console.log('Hiding loading screen...');
        hideLoading();
    }, 5000); // Hide loading after 5 seconds
}

export function payButtonHandler() {
    console.log('Starting payment process...');
    showLoading('Processing your payment...');
    setTimeout(() => {
        fetch('/pay', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
        })
            .then((response) => response.json())
            .then((data) => {
                console.log('Test Payment Response:', data);
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    showAlertMessage('Payment failed. Please try again.');
                    hideLoading();
                }
            });
    }, 1000);
}

