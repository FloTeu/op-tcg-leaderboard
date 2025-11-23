// Card Modal Global Functions
// These functions are globally accessible for card modal interactions

// Store the original URL before modal opens (global variable)
window.originalUrlBeforeModal = window.originalUrlBeforeModal || null;

// Update URL with card ID parameter
window.updateURLWithCardId = function(cardId) {
    const currentUrl = new URL(window.location);
    const currentCardId = currentUrl.searchParams.get('card_id');

    // If card_id already matches in URL, don't update (shared link case)
    if (currentCardId === cardId) {
        return;
    }

    // Store the original URL if not already stored
    if (!window.originalUrlBeforeModal) {
        window.originalUrlBeforeModal = window.location.href;
    }

    const url = new URL(window.location);
    // Only change pathname if not already on card-popularity page
    if (!url.pathname.includes('card-popularity')) {
        url.pathname = '/card-popularity';
    }
    url.searchParams.set('card_id', cardId);
    window.history.pushState({cardId: cardId}, '', url);
}

// Close card modal and restore URL
window.closeCardModal = function() {
    // Remove all modal backdrops
    document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove());

    // Restore the original URL before modal was opened
    if (window.originalUrlBeforeModal) {
        window.history.pushState({}, '', window.originalUrlBeforeModal);
        window.originalUrlBeforeModal = null;
    } else {
        // Fallback: just remove card_id parameter if no original URL stored
        const url = new URL(window.location);
        url.searchParams.delete('card_id');
        window.history.replaceState({}, '', url);
    }
}

// Set navigation height to match top card section
window.setNavigationHeight = function() {
    const cardContentSection = document.querySelector('.flex.flex-col.md\\:flex-row.gap-6.mb-6');
    const navLeft = document.querySelector('.card-nav-top-section.card-nav-left');
    const navRight = document.querySelector('.card-nav-top-section.card-nav-right');

    if (cardContentSection && navLeft && navRight) {
        const height = cardContentSection.offsetHeight;
        navLeft.style.height = height + 'px';
        navRight.style.height = height + 'px';
    }
}

// Get carousel container element
window.getCarouselContainer = function(element) {
    return element.closest('.modal-backdrop').querySelector('.carousel-item').parentElement;
}

// Update price display
window.updatePrice = function(activeItem) {
    const priceElement = document.getElementById('card-price');
    if (priceElement) {
        const price = activeItem.getAttribute('data-price');
        const currency = activeItem.getAttribute('data-currency');
        const eurPrice = activeItem.getAttribute('data-eur-price');
        const usdPrice = activeItem.getAttribute('data-usd-price');

        if (eurPrice && usdPrice && eurPrice !== 'N/A' && usdPrice !== 'N/A') {
            // Show both currencies when available
            priceElement.textContent = `€${eurPrice} | $${usdPrice}`;
        } else if (price === 'N/A') {
            priceElement.textContent = 'N/A';
        } else {
            priceElement.textContent = currency === 'EUR' ?
                `€${price}` :
                `$${price}`;
        }
    }
}

// Show specific carousel item
window.showCarouselItem = function(element, index) {
    const container = window.getCarouselContainer(element);
    const items = container.querySelectorAll('.carousel-item');
    const dots = container.querySelectorAll('.carousel-dot');

    items.forEach(item => item.classList.remove('active'));
    items[index].classList.add('active');

    // Update price for the active item
    window.updatePrice(items[index]);

    if (dots.length > 0) {
        dots.forEach((dot, i) => {
            dot.classList.toggle('bg-white', i === index);
            dot.classList.toggle('bg-white/50', i !== index);
        });
    }
}

// Navigate to next carousel item
window.nextCarouselItem = function(element) {
    const container = window.getCarouselContainer(element);
    const items = container.querySelectorAll('.carousel-item');
    const currentIndex = Array.from(items).findIndex(item => item.classList.contains('active'));
    const nextIndex = (currentIndex + 1) % items.length;
    window.showCarouselItem(element, nextIndex);
}

// Navigate to previous carousel item
window.previousCarouselItem = function(element) {
    const container = window.getCarouselContainer(element);
    const items = container.querySelectorAll('.carousel-item');
    const currentIndex = Array.from(items).findIndex(item => item.classList.contains('active'));
    const prevIndex = (currentIndex - 1 + items.length) % items.length;
    window.showCarouselItem(element, prevIndex);
}

// Event Listeners

// Update URL when modal is opened via HTMX
document.addEventListener('htmx:afterSettle', function(evt) {
    // Check if a modal backdrop was added to the body
    const modalBackdrop = document.querySelector('.modal-backdrop[data-card-id]');
    if (modalBackdrop && evt.detail.target === document.body) {
        const cardId = modalBackdrop.getAttribute('data-card-id');
        if (cardId) {
            window.updateURLWithCardId(cardId);
        }

        // Set the height of navigation areas to match the top card section
        window.setNavigationHeight();
    }
});

// Also set navigation height on window resize
window.addEventListener('resize', window.setNavigationHeight);

// Handle browser back/forward buttons
window.addEventListener('popstate', function(event) {
    const url = new URL(window.location);
    const cardId = url.searchParams.get('card_id');

    if (!cardId) {
        // Close modal if card_id is removed from URL
        document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove());
    }
});

// Keyboard navigation
document.addEventListener('keydown', (e) => {
    const activeModal = document.querySelector('.modal-backdrop');
    if (!activeModal) return;

    if (e.key === 'Escape') {
        e.preventDefault();
        window.closeCardModal();
    } else if (e.key === 'ArrowLeft') {
        window.previousCarouselItem(activeModal);
    } else if (e.key === 'ArrowRight') {
        window.nextCarouselItem(activeModal);
    }
});

// Touch support for mobile card navigation
document.addEventListener('DOMContentLoaded', function() {
    // Use event delegation since modal might not exist yet
    document.body.addEventListener('touchstart', function(e) {
        if (e.target.classList.contains('card-nav-left') || e.target.closest('.card-nav-left')) {
            e.preventDefault();
            const target = e.target.classList.contains('card-nav-left') ? e.target : e.target.closest('.card-nav-left');
            target.click();
        } else if (e.target.classList.contains('card-nav-right') || e.target.closest('.card-nav-right')) {
            e.preventDefault();
            const target = e.target.classList.contains('card-nav-right') ? e.target : e.target.closest('.card-nav-right');
            target.click();
        }
    });
});

