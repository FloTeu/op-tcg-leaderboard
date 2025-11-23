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

// Get all loaded card IDs from the DOM (for infinite scroll pages)
window.getAllLoadedCardIds = function() {
    const cardElements = [];

    // Look for card images with hx-get attributes that contain card-modal
    document.querySelectorAll('img[hx-get*="card-modal"]').forEach(img => {
        const hxGet = img.getAttribute('hx-get');
        if (hxGet) {
            const match = hxGet.match(/card_id=([^&]+)/);
            if (match && match[1]) {
                cardElements.push(match[1]);
            }
        }
    });

    return cardElements;
}

// Update card navigation visibility based on position
window.updateCardNavigationVisibility = function() {
    const activeModal = document.querySelector('.modal-backdrop');
    if (!activeModal) return;

    const currentCardId = activeModal.getAttribute('data-card-id');
    if (!currentCardId) return;

    const allCardIds = window.getAllLoadedCardIds();
    const currentIndex = allCardIds.indexOf(currentCardId);

    const navLeft = activeModal.querySelector('.card-nav-left');
    const navRight = activeModal.querySelector('.card-nav-right');

    if (navLeft) {
        navLeft.style.opacity = currentIndex > 0 ? '1' : '0.3';
        navLeft.style.cursor = currentIndex > 0 ? 'pointer' : 'not-allowed';
    }

    if (navRight) {
        navRight.style.opacity = currentIndex < allCardIds.length - 1 ? '1' : '0.3';
        navRight.style.cursor = currentIndex < allCardIds.length - 1 ? 'pointer' : 'not-allowed';
    }
}

// Flag to prevent rapid navigation
let isNavigating = false;

// Navigate to previous card
window.navigateToPreviousCard = function(currentCardId, event) {
    // Prevent rapid consecutive navigations
    if (isNavigating) return;

    // Stop event propagation to prevent modal close
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    const allCardIds = window.getAllLoadedCardIds();
    const currentIndex = allCardIds.indexOf(currentCardId);

    if (currentIndex > 0) {
        isNavigating = true;

        const prevCardId = allCardIds[currentIndex - 1];
        const cardElementsParam = allCardIds.map(id => `card_elements=${id}`).join('&');

        // Get current filter values
        const metaFormat = document.querySelector('[name="meta_format"]')?.value || 'latest';
        const currency = document.querySelector('[name="currency"]')?.value || 'eur';

        // Close current modal and load new one
        document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove());

        // Load new modal
        fetch(`/api/card-modal?card_id=${prevCardId}&${cardElementsParam}&meta_format=${metaFormat}&currency=${currency}`)
            .then(response => response.text())
            .then(html => {
                document.body.insertAdjacentHTML('beforeend', html);
                htmx.process(document.body);
                // Reset navigation flag after modal is loaded
                setTimeout(() => { isNavigating = false; }, 300);
            })
            .catch(error => {
                console.error('Error loading card modal:', error);
                isNavigating = false;
            });
    }
}

// Navigate to next card
window.navigateToNextCard = function(currentCardId, event) {
    // Prevent rapid consecutive navigations
    if (isNavigating) return;

    // Stop event propagation to prevent modal close
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    const allCardIds = window.getAllLoadedCardIds();
    const currentIndex = allCardIds.indexOf(currentCardId);

    if (currentIndex >= 0 && currentIndex < allCardIds.length - 1) {
        isNavigating = true;

        const nextCardId = allCardIds[currentIndex + 1];
        const cardElementsParam = allCardIds.map(id => `card_elements=${id}`).join('&');

        // Get current filter values
        const metaFormat = document.querySelector('[name="meta_format"]')?.value || 'latest';
        const currency = document.querySelector('[name="currency"]')?.value || 'eur';

        // Close current modal and load new one
        document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove());

        // Load new modal
        fetch(`/api/card-modal?card_id=${nextCardId}&${cardElementsParam}&meta_format=${metaFormat}&currency=${currency}`)
            .then(response => response.text())
            .then(html => {
                document.body.insertAdjacentHTML('beforeend', html);
                htmx.process(document.body);
                // Reset navigation flag after modal is loaded
                setTimeout(() => { isNavigating = false; }, 300);
            })
            .catch(error => {
                console.error('Error loading card modal:', error);
                isNavigating = false;
            });
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
            priceElement.textContent = currency === 'eur' ?
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

        // Update navigation visibility based on card position
        window.updateCardNavigationVisibility();
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
        // Arrow left: previous carousel item (card version)
        window.previousCarouselItem(activeModal);
    } else if (e.key === 'ArrowRight') {
        // Arrow right: next carousel item (card version)
        window.nextCarouselItem(activeModal);
    } else if (e.key === ',' || e.key === '<') {
        // Comma/< : previous card in grid
        e.preventDefault();
        const currentCardId = activeModal.getAttribute('data-card-id');
        if (currentCardId) {
            window.navigateToPreviousCard(currentCardId, e);
        }
    } else if (e.key === '.' || e.key === '>') {
        // Period/> : next card in grid
        e.preventDefault();
        const currentCardId = activeModal.getAttribute('data-card-id');
        if (currentCardId) {
            window.navigateToNextCard(currentCardId, e);
        }
    }
});

// Touch support for mobile card navigation
// Track touch gestures properly to avoid buggy behavior
let touchStartTarget = null;
let touchStartTime = 0;
const TOUCH_MOVE_THRESHOLD = 10; // pixels

document.addEventListener('DOMContentLoaded', function() {
    // Track where touch started
    document.body.addEventListener('touchstart', function(e) {
        const navElement = e.target.closest('.card-nav-left, .card-nav-right');
        if (navElement) {
            touchStartTarget = navElement;
            touchStartTime = Date.now();
            e.preventDefault(); // Prevent default touch behavior
            e.stopPropagation(); // Prevent propagation to backdrop
        }
    }, { passive: false });

    // Only trigger navigation if touch ends on the same element
    document.body.addEventListener('touchend', function(e) {
        if (!touchStartTarget) return;

        const touchDuration = Date.now() - touchStartTime;
        const navElement = e.target.closest('.card-nav-left, .card-nav-right');

        // Only proceed if touch ended on same navigation element and was quick enough (< 500ms)
        if (navElement && navElement === touchStartTarget && touchDuration < 500) {
            e.preventDefault();
            e.stopPropagation();

            const currentCardId = navElement.getAttribute('data-current-card-id');
            if (currentCardId) {
                if (navElement.classList.contains('card-nav-left')) {
                    window.navigateToPreviousCard(currentCardId, e);
                } else if (navElement.classList.contains('card-nav-right')) {
                    window.navigateToNextCard(currentCardId, e);
                }
            }
        }

        // Reset touch tracking
        touchStartTarget = null;
        touchStartTime = 0;
    }, { passive: false });

    // Cancel touch if user moves finger away
    document.body.addEventListener('touchmove', function(e) {
        if (touchStartTarget) {
            const navElement = e.target.closest('.card-nav-left, .card-nav-right');
            // If moved to different element, cancel the touch
            if (!navElement || navElement !== touchStartTarget) {
                touchStartTarget = null;
                touchStartTime = 0;
            }
        }
    }, { passive: true });

    // Cancel touch if interrupted
    document.body.addEventListener('touchcancel', function(e) {
        touchStartTarget = null;
        touchStartTime = 0;
    }, { passive: true });
});

