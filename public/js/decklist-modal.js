// Global variables to track current image and all available images
if (typeof window.decklistCurrentIndex === 'undefined') {
    window.decklistCurrentIndex = 0;
}

if (typeof window.decklistImages === 'undefined') {
    window.decklistImages = [];
}

if (typeof window.decklistCardIds === 'undefined') {
    window.decklistCardIds = [];
}

// Flag to prevent rapid swiping
if (typeof window.isSwiping === 'undefined') {
    window.isSwiping = false;
}

// Open the modal with the clicked image
function openDecklistModal(imgElement) {
    const modal = document.getElementById("decklistModal");
    const modalImg = document.getElementById("decklist-modal-img");
    const container = document.querySelector('.decklist-list-container');
    
    if (modal && modalImg && container) {
        // Get container position and dimensions
        const containerRect = container.getBoundingClientRect();
        
        // Set modal dimensions and position to match container
        modal.style.width = `${containerRect.width}px`;
        modal.style.height = `${containerRect.height}px`;
        modal.style.top = `${containerRect.top}px`;
        modal.style.left = `${containerRect.left}px`;
        
        // Set image source and display modal
        modal.style.display = "block";
        modalImg.src = imgElement.querySelector('img').src;
        
        // Store current image index, all image sources, and card IDs
        const imageElements = [
            ...document.querySelectorAll('.decklist-image'),
            ...document.querySelectorAll('.cursor-pointer[data-card-id]')
        ];
        
        window.decklistImages = imageElements.map(el => el.querySelector('img').src);
        window.decklistCardIds = imageElements.map(el => el.dataset.cardId || '');
        
        window.decklistCurrentIndex = parseInt(imgElement.dataset.index);
        
        // Add click event listener to close modal when clicking outside image
        modal.onclick = function(event) {
            // Only close if clicking the modal background (not the image)
            if (event.target === modal) {
                closeDecklistModal();
            }
        };
        
        // Add click event listener for image navigation and card modal
        modalImg.onclick = function(event) {
            event.stopPropagation(); // Prevent modal close when clicking image
            const imgWidth = this.getBoundingClientRect().width;
            const clickX = event.clientX - this.getBoundingClientRect().left;
            
            if (clickX < imgWidth / 4) {
                // Clicked on the left quarter - show previous image
                showPreviousImage();
            } else if (clickX > (imgWidth * 3) / 4) {
                // Clicked on the right quarter - show next image
                showNextImage();
            } else {
                // Clicked on the center area - open card modal
                openCardModalFromDecklist();
            }
        };
        
        // Update modal position and dimensions on scroll
        const updateModalPosition = () => {
            const newContainerRect = container.getBoundingClientRect();
            modal.style.width = `${newContainerRect.width}px`;
            modal.style.height = `${newContainerRect.height}px`;
            modal.style.top = `${newContainerRect.top}px`;
            modal.style.left = `${newContainerRect.left}px`;
        };
        
        // Add scroll event listener
        window.addEventListener('scroll', updateModalPosition);
        
        // Remove scroll event listener when modal is closed
        const originalCloseModal = window.closeDecklistModal;
        window.closeDecklistModal = function() {
            window.removeEventListener('scroll', updateModalPosition);
            if (originalCloseModal) {
                originalCloseModal();
            } else {
                modal.style.display = "none";
            }
        };
    }
}

// Close the modal
function closeDecklistModal() {
    const modal = document.getElementById("decklistModal");
    if (modal) {
        modal.style.display = "none";
    }
}

// Navigate to the previous image
function showPreviousImage() {
    if (window.decklistImages.length === 0 || window.isSwiping) return;
    
    window.isSwiping = true;
    window.decklistCurrentIndex = (window.decklistCurrentIndex - 1 + window.decklistImages.length) % window.decklistImages.length;
    const modalImg = document.getElementById("decklist-modal-img");
    if (modalImg) {
        modalImg.src = window.decklistImages[window.decklistCurrentIndex];
    }
    
    setTimeout(() => {
        window.isSwiping = false;
    }, 300);
}

// Navigate to the next image
function showNextImage() {
    if (window.decklistImages.length === 0 || window.isSwiping) return;
    
    window.isSwiping = true;
    window.decklistCurrentIndex = (window.decklistCurrentIndex + 1) % window.decklistImages.length;
    const modalImg = document.getElementById("decklist-modal-img");
    if (modalImg) {
        modalImg.src = window.decklistImages[window.decklistCurrentIndex];
    }
    
    setTimeout(() => {
        window.isSwiping = false;
    }, 300);
}

// Open card modal with detailed card information
function openCardModalFromDecklist() {
    // Get the current card ID
    if (!window.decklistCardIds || window.decklistCurrentIndex >= window.decklistCardIds.length) {
        console.warn('Card ID not available for current image');
        return;
    }
    
    const cardId = window.decklistCardIds[window.decklistCurrentIndex];
    if (!cardId) {
        console.warn('No card ID found for index:', window.decklistCurrentIndex);
        return;
    }
    
    // Close the decklist modal first to prevent overlapping
    closeDecklistModal();
    
    // Get meta format from URL or use 'latest' as default
    const urlParams = new URLSearchParams(window.location.search);
    const metaFormat = urlParams.get('meta_format') || 'latest';
    const currency = urlParams.get('currency') || 'EUR';
    
    // Use HTMX to trigger the card modal
    const url = `/api/card-modal?card_id=${encodeURIComponent(cardId)}&meta_format=${encodeURIComponent(metaFormat)}&currency=${encodeURIComponent(currency)}`;
    
    // Create a temporary element to trigger HTMX
    const tempElement = document.createElement('div');
    tempElement.setAttribute('hx-get', url);
    tempElement.setAttribute('hx-target', 'body');
    tempElement.setAttribute('hx-swap', 'beforeend');
    document.body.appendChild(tempElement);
    
    // Initialize HTMX on the element and trigger the request
    if (typeof htmx !== 'undefined') {
        htmx.process(tempElement);
        htmx.trigger(tempElement, 'click');
    }
    
    // Clean up after a short delay
    setTimeout(() => {
        if (tempElement.parentNode) {
            tempElement.parentNode.removeChild(tempElement);
        }
    }, 100);
}

// Set up event listeners
if (typeof window.decklistModalInitialized === 'undefined') {
    window.decklistModalInitialized = true;
    
    document.addEventListener('DOMContentLoaded', function() {
        const modal = document.getElementById("decklistModal");
        
        // Keyboard navigation
        document.addEventListener('keydown', function(event) {
            if (!modal || modal.style.display !== "block") return;
            
            if (event.key === "Escape") {
                closeDecklistModal();
            } else if (event.key === "ArrowLeft") {
                showPreviousImage();
            } else if (event.key === "ArrowRight") {
                showNextImage();
            }
        });
    });
} 