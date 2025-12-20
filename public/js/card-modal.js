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

    // First, check if we're in a decklist modal context
    const decklistModal = document.querySelector('.decklist-modal-backdrop, [id^="decklist-modal"]');

    if (decklistModal) {
        // If in decklist modal, only get cards from within that modal
        decklistModal.querySelectorAll('img[hx-get*="card-modal"]').forEach(img => {
            const hxGet = img.getAttribute('hx-get');
            if (hxGet) {
                const match = hxGet.match(/card_id=([^&]+)/);
                if (match && match[1]) {
                    cardElements.push(match[1]);
                }
            }
        });
    } else {
        // Otherwise, look for card images globally with hx-get attributes that contain card-modal
        document.querySelectorAll('img[hx-get*="card-modal"]').forEach(img => {
            const hxGet = img.getAttribute('hx-get');
            if (hxGet) {
                const match = hxGet.match(/card_id=([^&]+)/);
                if (match && match[1]) {
                    cardElements.push(match[1]);
                }
            }
        });
    }

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

// Cache for prefetched modals
const modalCache = new Map();
const MAX_CACHE_SIZE = 3;

// Prefetch adjacent card modals for faster navigation
function prefetchAdjacentModals(currentCardId) {
    const allCardIds = window.getAllLoadedCardIds();
    const currentIndex = allCardIds.indexOf(currentCardId);

    if (currentIndex < 0) return;

    const metaFormat = document.querySelector('[name="meta_format"]')?.value || 'latest';
    const currency = document.querySelector('[name="currency"]')?.value || 'eur';
    const cardElementsParam = allCardIds.map(id => `card_elements=${id}`).join('&');

    // Prefetch previous card
    if (currentIndex > 0) {
        const prevCardId = allCardIds[currentIndex - 1];
        const cacheKey = `${prevCardId}-${metaFormat}-${currency}`;

        if (!modalCache.has(cacheKey)) {
            fetch(`/api/card-modal?card_id=${prevCardId}&${cardElementsParam}&meta_format=${metaFormat}&currency=${currency}`)
                .then(response => response.text())
                .then(html => {
                    // Limit cache size
                    if (modalCache.size >= MAX_CACHE_SIZE) {
                        const firstKey = modalCache.keys().next().value;
                        modalCache.delete(firstKey);
                    }
                    modalCache.set(cacheKey, html);
                })
                .catch(error => console.error('Prefetch error:', error));
        }
    }

    // Prefetch next card
    if (currentIndex < allCardIds.length - 1) {
        const nextCardId = allCardIds[currentIndex + 1];
        const cacheKey = `${nextCardId}-${metaFormat}-${currency}`;

        if (!modalCache.has(cacheKey)) {
            fetch(`/api/card-modal?card_id=${nextCardId}&${cardElementsParam}&meta_format=${metaFormat}&currency=${currency}`)
                .then(response => response.text())
                .then(html => {
                    // Limit cache size
                    if (modalCache.size >= MAX_CACHE_SIZE) {
                        const firstKey = modalCache.keys().next().value;
                        modalCache.delete(firstKey);
                    }
                    modalCache.set(cacheKey, html);
                })
                .catch(error => console.error('Prefetch error:', error));
        }
    }
}

// Create a transparent overlay to block interactions during modal transition
function createTransitionOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'modal-transition-overlay';
    overlay.style.cssText = 'position: fixed; inset: 0; z-index: 9999; background: transparent; cursor: wait;';
    document.body.appendChild(overlay);
    return overlay;
}

// Remove transition overlay
function removeTransitionOverlay() {
    const overlay = document.getElementById('modal-transition-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// Navigate to previous card
window.navigateToPreviousCard = function(currentCardId, event) {
    // Stop event propagation to prevent modal close - do this FIRST
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    // Prevent rapid consecutive navigations
    if (isNavigating) return;

    const allCardIds = window.getAllLoadedCardIds();

    // If no cards found or current card not in list, do nothing (but don't let click bubble)
    if (allCardIds.length === 0) {
        console.warn('No card IDs found in DOM');
        return;
    }

    const currentIndex = allCardIds.indexOf(currentCardId);

    if (currentIndex < 0) {
        console.warn('Current card not found in loaded cards:', currentCardId);
        return;
    }

    if (currentIndex > 0) {
        isNavigating = true;

        // Immediately create overlay to block interactions
        const transitionOverlay = createTransitionOverlay();

        const prevCardId = allCardIds[currentIndex - 1];
        const cardElementsParam = allCardIds.map(id => `card_elements=${id}`).join('&');

        // Get current filter values
        const metaFormat = document.querySelector('[name="meta_format"]')?.value || 'latest';
        const currency = document.querySelector('[name="currency"]')?.value || 'eur';

        const cacheKey = `${prevCardId}-${metaFormat}-${currency}`;

        // Check if we have cached version
        let fetchPromise;
        if (modalCache.has(cacheKey)) {
            // Use cached version for instant load
            fetchPromise = Promise.resolve(modalCache.get(cacheKey));
            modalCache.delete(cacheKey); // Remove from cache after use
        } else {
            // Fetch from server
            fetchPromise = fetch(`/api/card-modal?card_id=${prevCardId}&${cardElementsParam}&meta_format=${metaFormat}&currency=${currency}`)
                .then(response => response.text());
        }

        // Close current modal while fetching
        document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove());

        // Wait for fetch to complete, then insert
        fetchPromise
            .then(html => {
                document.body.insertAdjacentHTML('beforeend', html);
                htmx.process(document.body);
                // Remove overlay and reset flag immediately after insertion
                removeTransitionOverlay();
                isNavigating = false;
                // Prefetch adjacent modals for next navigation
                setTimeout(() => prefetchAdjacentModals(prevCardId), 100);
            })
            .catch(error => {
                console.error('Error loading card modal:', error);
                removeTransitionOverlay();
                isNavigating = false;
            });
    }
}

// Navigate to next card
window.navigateToNextCard = function(currentCardId, event) {
    // Stop event propagation to prevent modal close - do this FIRST
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    // Prevent rapid consecutive navigations
    if (isNavigating) return;

    const allCardIds = window.getAllLoadedCardIds();

    // If no cards found or current card not in list, do nothing (but don't let click bubble)
    if (allCardIds.length === 0) {
        console.warn('No card IDs found in DOM');
        return;
    }

    const currentIndex = allCardIds.indexOf(currentCardId);

    if (currentIndex < 0) {
        console.warn('Current card not found in loaded cards:', currentCardId);
        return;
    }

    if (currentIndex >= 0 && currentIndex < allCardIds.length - 1) {
        isNavigating = true;

        // Immediately create overlay to block interactions
        const transitionOverlay = createTransitionOverlay();

        const nextCardId = allCardIds[currentIndex + 1];
        const cardElementsParam = allCardIds.map(id => `card_elements=${id}`).join('&');

        // Get current filter values
        const metaFormat = document.querySelector('[name="meta_format"]')?.value || 'latest';
        const currency = document.querySelector('[name="currency"]')?.value || 'eur';

        const cacheKey = `${nextCardId}-${metaFormat}-${currency}`;

        // Check if we have cached version
        let fetchPromise;
        if (modalCache.has(cacheKey)) {
            // Use cached version for instant load
            fetchPromise = Promise.resolve(modalCache.get(cacheKey));
            modalCache.delete(cacheKey); // Remove from cache after use
        } else {
            // Fetch from server
            fetchPromise = fetch(`/api/card-modal?card_id=${nextCardId}&${cardElementsParam}&meta_format=${metaFormat}&currency=${currency}`)
                .then(response => response.text());
        }

        // Close current modal while fetching
        document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove());

        // Wait for fetch to complete, then insert
        fetchPromise
            .then(html => {
                document.body.insertAdjacentHTML('beforeend', html);
                htmx.process(document.body);
                // Remove overlay and reset flag immediately after insertion
                removeTransitionOverlay();
                isNavigating = false;
                // Prefetch adjacent modals for next navigation
                setTimeout(() => prefetchAdjacentModals(nextCardId), 100);
            })
            .catch(error => {
                console.error('Error loading card modal:', error);
                removeTransitionOverlay();
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

    // Update price chart for the active item
    const cardId = items[index].getAttribute('data-card-id');
    const aaVersion = items[index].getAttribute('data-aa-version');

    if (cardId) {
        const modalBackdrop = container.closest('.modal-backdrop');
        if (modalBackdrop) {
            const priceChartContainer = modalBackdrop.querySelector('[id^="price-chart-container-"]');
            const priceChartLoading = modalBackdrop.querySelector('[id^="price-chart-loading-"]');
            const pricePeriodSelector = modalBackdrop.querySelector('[id^="price-period-selector-"]');

            if (priceChartContainer && priceChartLoading && pricePeriodSelector) {
                // Update IDs to match new card ID
                priceChartContainer.id = `price-chart-container-${cardId}`;
                priceChartLoading.id = `price-chart-loading-${cardId}`;
                pricePeriodSelector.id = `price-period-selector-${cardId}`;

                // Update hx-vals in selector
                const days = pricePeriodSelector.value;
                const aaVersionParam = aaVersion !== null ? `, "aa_version": "${aaVersion}"` : '';
                pricePeriodSelector.setAttribute('hx-vals', `js:{"card_id": "${cardId}", "days": document.getElementById("price-period-selector-${cardId}").value, "include_alt_art": "false"${aaVersionParam}}`);
                pricePeriodSelector.setAttribute('hx-target', `#price-chart-container-${cardId}`);
                pricePeriodSelector.setAttribute('hx-indicator', `#price-chart-loading-${cardId}`);
                pricePeriodSelector.setAttribute('hx-on::before-request', `document.getElementById('price-chart-container-${cardId}').innerHTML = ''; document.getElementById('price-chart-loading-${cardId}').style.display = 'flex';`);

                // Trigger HTMX request to update chart
                let url = `/api/card-price-development-chart?card_id=${cardId}&days=${days}`;
                if (aaVersion !== null) {
                    url += `&aa_version=${aaVersion}`;
                }

                htmx.ajax('GET', url, {
                    target: `#price-chart-container-${cardId}`,
                    indicator: `#price-chart-loading-${cardId}`
                });
            }
        }
    }

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

        // Prefetch adjacent modals for instant navigation
        if (cardId) {
            setTimeout(() => prefetchAdjacentModals(cardId), 100);
        }
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
// Track touch gestures properly to avoid buggy behavior while allowing scroll
let touchStartTarget = null;
let touchStartTime = 0;
let touchStartY = 0;
let touchStartX = 0;
let hasScrolled = false;
const SCROLL_THRESHOLD = 10; // pixels - if moved more than this, consider it a scroll

document.addEventListener('DOMContentLoaded', function() {
    // Track where touch started
    document.body.addEventListener('touchstart', function(e) {
        const navElement = e.target.closest('.card-nav-left, .card-nav-right');
        if (navElement) {
            touchStartTarget = navElement;
            touchStartTime = Date.now();
            touchStartY = e.touches[0].clientY;
            touchStartX = e.touches[0].clientX;
            hasScrolled = false;
            // Don't prevent default here - allow scrolling to work
        }
    }, { passive: true });

    // Detect if user is scrolling
    document.body.addEventListener('touchmove', function(e) {
        if (touchStartTarget) {
            const currentY = e.touches[0].clientY;
            const currentX = e.touches[0].clientX;
            const deltaY = Math.abs(currentY - touchStartY);
            const deltaX = Math.abs(currentX - touchStartX);

            // If moved vertically more than threshold, it's a scroll
            if (deltaY > SCROLL_THRESHOLD) {
                hasScrolled = true;
                touchStartTarget = null; // Cancel navigation
            }
            // If moved horizontally to different element, cancel
            else if (deltaX > SCROLL_THRESHOLD) {
                const navElement = e.target.closest('.card-nav-left, .card-nav-right');
                if (!navElement || navElement !== touchStartTarget) {
                    touchStartTarget = null;
                }
            }
        }
    }, { passive: true });

    // Only trigger navigation if touch ends on the same element and user didn't scroll
    document.body.addEventListener('touchend', function(e) {
        if (!touchStartTarget || hasScrolled) {
            // Reset and don't navigate
            touchStartTarget = null;
            hasScrolled = false;
            touchStartTime = 0;
            return;
        }

        const touchDuration = Date.now() - touchStartTime;
        const navElement = e.target.closest('.card-nav-left, .card-nav-right');

        // Only proceed if:
        // 1. Touch ended on same navigation element
        // 2. Was quick enough (< 500ms)
        // 3. User didn't scroll
        if (navElement && navElement === touchStartTarget && touchDuration < 500 && !hasScrolled) {
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
        hasScrolled = false;
    }, { passive: false });

    // Cancel touch if interrupted
    document.body.addEventListener('touchcancel', function(e) {
        touchStartTarget = null;
        touchStartTime = 0;
        hasScrolled = false;
    }, { passive: true });
});

