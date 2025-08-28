import {flash, retakeButton} from './dom.js';
export let selectedTimer = null; // Initialize selected timer

// Set the selected timer when a menu item is clicked
export function setTimer(timer, element) {
    // Change the selected timer
    selectedTimer = timer;
    console.log('Selected timer:', selectedTimer);

    // Remove 'selected' from all menu items
    document.querySelectorAll('.menu-item').forEach((item) => {
        item.classList.remove('selected');
    });

    // Add 'selected' to the clicked one
    const clickedItem = event.target.closest('.menu-item');
    if (clickedItem) {
        clickedItem.classList.add('selected');
    }
}

// Show loading screen
export function showLoading(text) {
    document.getElementById('loading-element').style.display = 'block';
    document.getElementById('loading-text').style.display = 'block';
    document.getElementById('blur-overlay').style.display = 'block';
    document.getElementById('loading-text').textContent =
        text || 'Loading, please wait';
}

// Hide loading screen
export function hideLoading() {
    document.getElementById('loading-element').style.display = 'none';
    document.getElementById('loading-text').style.display = 'none';
    document.getElementById('blur-overlay').style.display = 'none';
}

// Show alert message using SweetAlert2
export function showAlertMessage(message) {
    Swal.fire({
        icon: 'error',
        title: 'Error',
        text: message,
        scrollbarPadding: false,
    });
}

// Only used for error on preview message
export async function showAlertWithAction(message) {
    const result = await Swal.fire({
        icon: 'error',
        title: 'Error',
        text: message,
        scrollbarPadding: false,
    });

    // result.isConfirmed will be true if user pressed OK
    if (result.isConfirmed) {
        retakeButton.click(); // Trigger retake button click
    }

}

// Show success message using SweetAlert2
function showSuccessMessage(title, message) {
    Swal.fire({
        icon: 'success',
        title: title,
        text: message,
    });
}

// Show confirmation message using SweetAlert2
export function showConfirmationMessage(
    title,
    message,
    confirmMessage,
    cancelMessage,
    linkYes,
    linkCancel,
) {
    linkCancel = linkCancel ?? null;
    Swal.fire({
        title: title,
        text: message,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: confirmMessage,
        cancelButtonText: cancelMessage,
    }).then((result) => {
        if (result.isConfirmed) {
            // User clicked confirm button
            window.location.href = linkYes; // Redirect to home page
        } else if (result.dismiss === Swal.DismissReason.cancel && linkCancel) {
            window.location.href = linkCancel; // Redirect to cancel page
        }
    });
}

// Start the camera with specified photo dimensions
export async function startCamera(photoWidth, photoHeight) {
    try {
        showLoading();

        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: photoWidth },
                height: { ideal: photoHeight },
            },
            audio: false,
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
        showAlertMessage(
            'Failed to access camera. Please check your camera settings or permissions.',
        );
    }
}

// Function to toggle flash for the camera
export function toggleFlash() {
    flash.classList.remove('flash-anim');
    void flash.offsetWidth;
    flash.classList.add('flash-anim');
}

// Function to toggle the dropdown visibility
export function toggleTimerDropdown() {
    const timerDropdown = document.getElementById('timerDropdown');
    timerDropdown.classList.toggle('hidden');
}

// Function to wait for video to be ready
export function waitForVideoReady(video) {
  return new Promise((resolve) => {
    if (video.videoWidth && video.videoHeight && video.readyState >= 2)
      return resolve();
    const onReady = () => {
      if (video.videoWidth && video.videoHeight && video.readyState >= 2) {
        video.removeEventListener('loadedmetadata', onReady);
        video.removeEventListener('canplay', onReady);
        resolve();
      }
    };
    video.addEventListener('loadedmetadata', onReady);
    video.addEventListener('canplay', onReady);
  });
}

export async function fetchFullImageUrl() {
    const res = await fetch('/get_full_original_filename_url', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    });
    if (!res.ok) {
        throw new Error('Failed to fetch full image URL');
    }
    const data = await res.json();
    const fullImageUrl = data?.full_image_filename_url;
    if (!fullImageUrl) {
        throw new Error('Full image URL not found in response');
    }
    console.log('Full image URL:', fullImageUrl);
    return fullImageUrl;
}
