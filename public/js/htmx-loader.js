// Conditionally load htmx.js only if not already loaded or if only stub is present
// This prevents double-loading when FastHTML includes htmx from CDN
// and provides fallback when CDN fails
(function() {
    'use strict';

    // Function to check if real htmx is loaded (not just the stub)
    function isRealHtmxLoaded() {
        if (typeof window.htmx === 'undefined') {
            return false;
        }
        // Check if it has core functionality (not just a stub)
        // Real htmx should have the ajax method and actual functionality
        return typeof window.htmx.ajax === 'function' &&
               typeof window.htmx.process === 'function' &&
               (window.htmx.version || window.htmx.config.version);
    }

    // Function to load self-hosted htmx
    function loadSelfHostedHtmx() {
        console.log('[htmx-loader] Loading self-hosted htmx.js');

        var script = document.createElement('script');
        script.src = '/public/js/htmx.js';
        script.async = false; // Ensure synchronous execution order
        script.onerror = function() {
            console.error('[htmx-loader] Failed to load self-hosted htmx.js');
        };
        script.onload = function() {
            console.log('[htmx-loader] Self-hosted htmx.js loaded successfully (version: ' + (window.htmx ? window.htmx.version : 'unknown') + ')');
            if (isRealHtmxLoaded()) {
                // Process any pending htmx elements
                try {
                    window.htmx.process(document.body);
                } catch(e) {
                    console.error('[htmx-loader] Error processing htmx elements:', e);
                }
            }
        };

        // Insert before the next script tag to maintain execution order
        var currentScript = document.currentScript || document.querySelector('script[src*="htmx-loader"]');
        if (currentScript && currentScript.parentNode) {
            currentScript.parentNode.insertBefore(script, currentScript.nextSibling);
        } else {
            document.head.appendChild(script);
        }
    }

    // Check immediately if htmx is already properly loaded
    if (isRealHtmxLoaded()) {
        console.log('[htmx-loader] htmx already loaded (version: ' + window.htmx.version + '), skipping self-hosted load');
        return;
    }

    // Check if only a stub exists (FastHTML's fallback stub)
    var hasStub = typeof window.htmx !== 'undefined' && !window.htmx.version;
    if (hasStub) {
        console.warn('[htmx-loader] htmx stub detected, waiting 1 second for CDN load before using self-hosted');
    } else {
        console.log('[htmx-loader] htmx not detected, waiting 1 second for CDN load before using self-hosted');
    }

    // Wait 1 second for FastHTML's CDN htmx to load (sometimes loads on second try)
    setTimeout(function() {
        if (isRealHtmxLoaded()) {
            console.log('[htmx-loader] htmx loaded from CDN (version: ' + window.htmx.version + ')');
        } else {
            console.log('[htmx-loader] htmx still not available after 1 second, loading self-hosted version');
            loadSelfHostedHtmx();
        }
    }, 1000);
})();

