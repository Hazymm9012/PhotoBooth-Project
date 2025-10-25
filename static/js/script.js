import {
    showConfirmationMessage,
    showAlertMessage,
    showLoading,
    hideLoading,
    startCamera,
    setTimer
} from "./utils.js";
import {
    previewPageButtons,
    payButtonHandler
} from "./buttons.js";
import {
    settings,
    payButton,
    logoutButton,
    exitButton,
    toggleButtons,
    menuLists,
    menuItems,
    menuItemsLinks,
    timerContainerButtons
} from "./dom.js";

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function () {
    const path = window.location.pathname;
    console.log('Path:', window.location.pathname);

    // Trigger animations for timer toggle button
    toggleButtons.forEach((btn) => {
        btn.addEventListener('click', function () {
            const captureButton = document.getElementById('captureButton');
            btn.classList.toggle('effect');

            if (btn.classList.contains('effect')) {
                captureButton.disabled = true;
            } else {
                captureButton.disabled = false;
            }
            menuLists.forEach((menu) => {
                menu.classList.toggle('effect');
            });

            void toggleButtons.offsetWidth; // Trigger reflow to ensure transition works
        });
    });

    // Add click event listeners to menu items
    menuItems.forEach((item) => {
        item.addEventListener('click', function () {
            menuLists.forEach((menu) => {
                menu.classList.remove('effect');
            });
            toggleButtons.forEach((btn) => {
                btn.classList.remove('effect');
            });
            document.getElementById('captureButton').disabled = false;
        });
    });

    // Set timer when menu item is clicked
    menuItemsLinks.forEach((link) => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const time = parseInt(this.dataset.time, 10);
            setTimer(time, link);
        });
    });

    // Exit button needs to load first.
    if (exitButton) {
        exitButton.addEventListener('click', (e) => {
            e.preventDefault();
            showConfirmationMessage(
                'Exit',
                'Are you sure you want to exit ?',
                'Exit',
                'Cancel',
                '/exit',
            );
        });
    }

    // Logout button (ADMIN ONLY).
    if (logoutButton) {
        logoutButton.addEventListener('click', (e) => {
            e.preventDefault();
            showConfirmationMessage(
                'Logout',
                'Are you sure you want to logout ?',
                'Logout',
                'Cancel',
                '/admin/logout',
            );
        });
    }

    // Handle payment fail page
    if (path === '/fail') {
        const status = new URLSearchParams(window.location.search).get('status');
        console.log('Payment status:', status);

        // Here, status can either be failed or canceled only
        if (status === 'canceled') {
            showConfirmationMessage(
                'Payment Cancelled',
                'You have cancelled your payment. Try again?',
                'Try Again',
                'Return Home',
                '/preview',
                '/exit',
            );
        } else {
            showConfirmationMessage(
                'Payment Failed',
                'Your payment has failed. Please try again.',
                'Try Again',
                'Return Home',
                '/preview',
                '/exit',
            );
        }
    }

    // Handle preview page
    if (path === '/preview') {
        // Get the video element
        const width = window.innerWidth;
        const height = window.innerHeight;
        // document.getElementById('timerButton').addEventListener('click', toggleTimerDropdown);

        // Get the video element
        const photoSession = settings.dataset.photoSession;
        var oldPhotoSizeNow = settings.dataset.oldPhotoSize;
        console.log('Old photo size from settings:', oldPhotoSizeNow);
        console.log('Photo session from Flask:', photoSession); 
        const photoWidth = parseInt(settings.dataset.photoWidth);
        const photoHeight = parseInt(settings.dataset.photoHeight);

        // Camera auto-load on preview page
        console.log('Photo dimensions from Flask:', photoWidth, photoHeight);

        // If the photo session is already set, display the photo
        const hasPhotoSession =
            photoSession && photoSession !== 'undefined' && photoSession !== 'null';
        const hasOldPhotoSize =
            oldPhotoSizeNow && oldPhotoSizeNow !== 'undefined' && oldPhotoSizeNow !== 'None';
        console.log('Has photo session:', hasPhotoSession);
        console.log('Has old photo size:', hasOldPhotoSize);
        if (
            hasPhotoSession &&
            (!hasOldPhotoSize || oldPhotoSizeNow === photoSession)
        ) {
            console.log('Photo session already exists:', photoSession);
            photo.src = `/static/preview_photos/${photoSession}`;
            previewPageButtons(photoWidth, photoHeight);

            // Adjust buttons configuration when previewing a photo
            photo.style.display = 'block';
            video.style.display = 'none';
            retakeButton.style.display = 'inline-block';
            uploadButton.style.display = 'inline-block';
            captureButton.style.display = 'none';
            paymentButton.style.display = 'inline-block';
            timerContainerButtons.style.display = 'none';
            //timerButton.style.display = "none";
        } else {
            console.log('No photo session found, starting camera...');
            // Request access to the user's camera
            // If no photo session exists, start the camera
            window.onload = function () {
                // Start the camera
                startCamera(photoWidth, photoHeight);

                // Show all the page buttons
                previewPageButtons(photoWidth, photoHeight);
            };
        }

        // This needs to be in "preview if" statement
        if (path === '/payment-summary') {
            //const photoFilename = {{ photo_filename }};
            window.onload = function () {
                const photoSummary = document.getElementById('photo-summary');
                const canvasSummary = document.getElementById('canvas-summary');
                photoSummary.src = '{{ photo_filename }}';
                photoSummary.style.display = 'block';
                setTimeout(() => {
                    hideLoading();
                    content.style.display = 'block';
                }, 500);
            };
        }
    }

    if (path === '/admin/download') {
        document
            .getElementById('download-form')
            .addEventListener('submit', async (e) => {
                e.preventDefault();
                showLoading();
                const code = e.target.unique_code.value;

                const response = await fetch('/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ unique_code: code }),
                });

                const data = await response.json();

                if (!response.ok) {
                    showAlertMessage(data.error);
                    hideLoading();
                    return;
                }

                setTimeout(() => {
                    window.location.href = data.url;
                    hideLoading();
                }, 1000);
            });
    }
});

document.querySelectorAll('.frame-button').forEach((button) => {
    button.addEventListener('click', function () {
        // Uncheck all buttons
        document
            .querySelectorAll('.frame-button')
            .forEach((b) => b.classList.remove('checked'));

        // Check clicked button
        this.classList.add('checked');
    });
});

// This needs to be declared outside of the DOMContentLoaded event
if (payButton) {
    payButton.addEventListener('click', function () {
        payButtonHandler();
    });
}

document.querySelectorAll('.frame-button').forEach((btn) => {
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
