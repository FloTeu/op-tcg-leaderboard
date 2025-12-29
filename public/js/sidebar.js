// Sidebar functionality
let sidebarState = {
    isOpen: false,
    isMobile: false
};

function isMobileDevice() {
    return window.innerWidth <= 768; // Tailwind's md breakpoint
}

function getCurrentSidebarState() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return false;
    
    // Check if sidebar is visible by checking its transform
    const transform = window.getComputedStyle(sidebar).transform;
    return transform === 'none' || transform === 'matrix(1, 0, 0, 1, 0, 0)';
}

function toggleBurgerMenu(isOpen) {
    // Only animate the sidebar burger menu lines (the one inside the sidebar)
    const sidebarBurgerMenu = document.getElementById('sidebar-burger-menu');
    const lines = document.querySelectorAll('#sidebar-burger-menu div div');
    
    if (lines.length >= 3) {
        if (isOpen) {
            // Transform to X
            lines[0].style.transform = 'translateY(8px) rotate(45deg)';
            lines[1].style.opacity = '0';
            lines[2].style.transform = 'translateY(-8px) rotate(-45deg)';
        } else {
            // Transform back to burger
            lines[0].style.transform = 'none';
            lines[1].style.opacity = '1';
            lines[2].style.transform = 'none';
        }
    }
}

function setSidebarState(isOpen) {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    const topBar = document.getElementById('top-bar');
    
    if (!sidebar || !mainContent || !topBar) {
        console.error('Required elements not found:', { sidebar: !!sidebar, mainContent: !!mainContent, topBar: !!topBar });
        return;
    }
    
    sidebarState.isOpen = isOpen;
    sidebarState.isMobile = isMobileDevice();
    
    // Handle elements that should be hidden when sidebar is open (mobile only)
    const hideOnOpenElements = document.querySelectorAll('.hide-on-sidebar-open');
    hideOnOpenElements.forEach(el => {
        if (isOpen && sidebarState.isMobile) {
             el.style.display = 'none';
        } else {
             el.style.display = '';
        }
    });

    if (sidebarState.isMobile) {
        // Mobile behavior
        if (isOpen) {
            sidebar.style.transform = 'translateX(0)';
            mainContent.style.marginLeft = '0';
            topBar.style.display = 'none';
            document.body.style.overflow = 'hidden'; // Prevent scrolling when sidebar is open
        } else {
            sidebar.style.transform = 'translateX(-100%)';
            mainContent.style.marginLeft = '0';
            topBar.style.display = 'block';
            document.body.style.overflow = ''; // Restore scrolling
        }
        toggleBurgerMenu(isOpen);
    } else {
        // Desktop behavior
        if (isOpen) {
            sidebar.style.transform = 'translateX(0)';
            mainContent.style.marginLeft = '320px';
            topBar.style.display = 'none';
            document.body.style.overflow = ''; // Always allow scrolling on desktop
        } else {
            sidebar.style.transform = 'translateX(-100%)';
            mainContent.style.marginLeft = '0';
            topBar.style.display = 'block';
            document.body.style.overflow = ''; // Always allow scrolling on desktop
        }
        toggleBurgerMenu(isOpen);
    }
}

function setInitialSidebarState() {
    const wasMobile = sidebarState.isMobile;
    const currentlyMobile = isMobileDevice();
    
    // First, detect the actual current state from DOM
    const actualState = getCurrentSidebarState();
    
    // On first load or when device type changes
    if (wasMobile !== currentlyMobile || (!wasMobile && !currentlyMobile && !sidebarState.isOpen)) {
        if (currentlyMobile) {
            // Mobile - close sidebar by default
            setSidebarState(false);
        } else {
            // Desktop - open sidebar by default
            setSidebarState(true);
        }
    } else {
        // Sync our state with the actual DOM state
        if (actualState !== sidebarState.isOpen) {
            sidebarState.isOpen = actualState;
            // Update burger menu animation to match actual state
            toggleBurgerMenu(actualState);
        }
    }
}

// Make toggleSidebar globally available
function toggleSidebar() {
    // Always sync with actual state before toggling
    const actualState = getCurrentSidebarState();
    setSidebarState(!actualState);
}

// Ensure it's available on window object for onclick handlers
window.toggleSidebar = toggleSidebar;

function closeSidebarOnOutsideClick(event) {
    // Only handle outside clicks on mobile when sidebar is open
    if (!sidebarState.isMobile || !sidebarState.isOpen) {
        return;
    }
    
    const sidebar = document.getElementById('sidebar');
    const topBar = document.getElementById('top-bar');
    
    // Check if click is outside sidebar and top bar
    if (sidebar && !sidebar.contains(event.target) && 
        topBar && !topBar.contains(event.target)) {
        setSidebarState(false);
    }
}

// Set initial state on load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize state properly
    sidebarState.isMobile = isMobileDevice();
    
    // Detect actual sidebar state from DOM instead of assuming false
    sidebarState.isOpen = getCurrentSidebarState();
    
    // Force correct initial state based on device type
    if (isMobileDevice()) {
        // On mobile, always start closed
        setSidebarState(false);
    } else {
        // On desktop, start open
        setSidebarState(true);
    }
    
    // Add outside click listener
    document.addEventListener('click', closeSidebarOnOutsideClick);
    
    // Close sidebar on mobile when any link in sidebar is clicked
    document.addEventListener('click', function(event) {
        // Check if the clicked element is a link inside the sidebar
        const clickedLink = event.target.closest('#sidebar a[href]');
        if (clickedLink && isMobileDevice()) {
            // Close sidebar immediately on mobile
            setSidebarState(false);
        }
    });
});

// Update on resize (with debouncing to prevent issues during scroll)
let resizeTimeout;
window.addEventListener('resize', function() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        // Sync state with actual DOM state before applying resize logic
        sidebarState.isOpen = getCurrentSidebarState();
        setInitialSidebarState();
    }, 150);
}); 
