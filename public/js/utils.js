// Tooltip functionality
function initializeTooltips() {
    // Create tooltip element if it doesn't exist
    let tooltipEl = document.getElementById('global-tooltip');
    if (!tooltipEl) {
        tooltipEl = document.createElement('div');
        tooltipEl.id = 'global-tooltip';
        tooltipEl.style.cssText = `
            position: fixed;
            display: none;
            padding: 8px 12px;
            background: rgba(17, 24, 39, 0.95);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 4px;
            font-size: 14px;
            max-width: 300px;
            z-index: 10000;
            pointer-events: none;
            transition: opacity 0.15s ease-in-out;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        `;
        document.body.appendChild(tooltipEl);
    }

    // Add event listeners to all tooltip triggers
    document.querySelectorAll('[data-tooltip]').forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
        element.addEventListener('mousemove', moveTooltip);
    });

    function showTooltip(e) {
        const tooltipText = this.getAttribute('data-tooltip');
        if (!tooltipText) return;

        tooltipEl.textContent = tooltipText;
        tooltipEl.style.display = 'block';
        moveTooltip.call(this, e);
    }

    function hideTooltip() {
        tooltipEl.style.display = 'none';
    }

    function moveTooltip(e) {
        const padding = 10;
        const tooltipWidth = tooltipEl.offsetWidth;
        const tooltipHeight = tooltipEl.offsetHeight;
        
        // Calculate position
        let x = e.clientX + padding;
        let y = e.clientY + padding;

        // Check if tooltip would go off screen
        if (x + tooltipWidth > window.innerWidth) {
            x = e.clientX - tooltipWidth - padding;
        }
        if (y + tooltipHeight > window.innerHeight) {
            y = e.clientY - tooltipHeight - padding;
        }

        tooltipEl.style.left = x + 'px';
        tooltipEl.style.top = y + 'px';
    }
}

// Initialize tooltips when the DOM is loaded
document.addEventListener('DOMContentLoaded', initializeTooltips);

// Re-initialize tooltips after HTMX content swaps
document.addEventListener('htmx:afterSwap', initializeTooltips); 