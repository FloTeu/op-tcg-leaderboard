class DoubleRangeSlider {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with id ${containerId} not found`);
            return;
        }

        this.minRange = this.container.querySelector('.min-range');
        this.maxRange = this.container.querySelector('.max-range');
        this.minValue = this.container.querySelector('.min-value');
        this.maxValue = this.container.querySelector('.max-value');
        this.sliderTrack = this.container.querySelector('.slider-track');

        if (!this.minRange || !this.maxRange || !this.minValue || !this.maxValue || !this.sliderTrack) {
            console.error('Required elements not found in container');
            return;
        }

        this.init();
    }

    updateSlider() {
        const min = parseInt(this.minRange.value);
        const max = parseInt(this.maxRange.value);
        const percentage = (value) => ((value - this.minRange.min) / (this.minRange.max - this.minRange.min)) * 100;

        // Update the values display with proper formatting
        this.minValue.textContent = min.toLocaleString();
        this.maxValue.textContent = max.toLocaleString();

        // Update track position using CSS variables
        this.sliderTrack.style.setProperty('--left-percent', `${percentage(min)}%`);
        this.sliderTrack.style.setProperty('--right-percent', `${100 - percentage(max)}%`);
    }

    init() {
        // Bind the event handlers
        this.minRange.addEventListener('input', () => {
            if (parseInt(this.minRange.value) > parseInt(this.maxRange.value)) {
                this.minRange.value = this.maxRange.value;
            }
            this.updateSlider();
        });

        this.maxRange.addEventListener('input', () => {
            if (parseInt(this.maxRange.value) < parseInt(this.minRange.value)) {
                this.maxRange.value = this.minRange.value;
            }
            this.updateSlider();
        });

        // Initialize the slider
        this.updateSlider();
    }
}

// Initialize all double range sliders on the page
function initializeDoubleRangeSliders() {
    document.querySelectorAll('[data-double-range-slider]').forEach(container => {
        // Avoid re-initializing already initialized sliders
        if (!container.hasAttribute('data-slider-initialized')) {
            new DoubleRangeSlider(container.id);
            container.setAttribute('data-slider-initialized', 'true');
        }
    });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initializeDoubleRangeSliders);

// Re-initialize after HTMX swaps (for dynamic content)
document.addEventListener('htmx:afterSwap', initializeDoubleRangeSliders); 