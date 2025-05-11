// Global variables to track current image and all available images
if (typeof window.decklistCurrentIndex === 'undefined') {
    window.decklistCurrentIndex = 0;
}

if (typeof window.decklistImages === 'undefined') {
    window.decklistImages = [];
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
        // Get container position relative to viewport
        const containerRect = container.getBoundingClientRect();
        
        // Position modal at the top left of the container, but within viewport
        const topPosition = Math.max(0, containerRect.top);
        const leftPosition = Math.max(0, containerRect.left);
        
        // Set modal position
        modal.style.top = `${topPosition}px`;
        modal.style.left = `${leftPosition}px`;
        
        // Set image source and display modal
        modal.style.display = "block";
        modalImg.src = imgElement.querySelector('img').src;
        
        // Store current image index and all image sources
        window.decklistImages = [
            ...document.querySelectorAll('.decklist-image img'),
            ...document.querySelectorAll('.cursor-pointer img')
        ].map(img => img.src);
        
        window.decklistCurrentIndex = parseInt(imgElement.dataset.index);
        
        // Add click event listener to close modal when clicking anywhere
        modal.onclick = function() {
            closeDecklistModal();
        };
        
        // Update modal position on scroll
        const updateModalPosition = () => {
            const newContainerRect = container.getBoundingClientRect();
            const newTopPosition = Math.max(0, newContainerRect.top);
            const newLeftPosition = Math.max(0, newContainerRect.left);
            
            modal.style.top = `${newTopPosition}px`;
            modal.style.left = `${newLeftPosition}px`;
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