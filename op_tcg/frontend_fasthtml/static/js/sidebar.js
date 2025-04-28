// Sidebar functionality
function isMobileDevice() {
    return window.innerWidth <= 768; // Tailwind's md breakpoint
}

function toggleBurgerMenu(isOpen) {
    const topBurgerMenu = document.getElementById('top-burger-menu');
    const sidebarBurgerMenu = document.getElementById('sidebar-burger-menu');
    const lines = document.querySelectorAll('#top-burger-menu div div, #sidebar-burger-menu div div');
    
    if (isOpen) {
        // Transform to X
        lines[0].style.transform = 'translateY(8px) rotate(45deg)';
        lines[1].style.opacity = '0';
        lines[2].style.transform = 'translateY(-8px) rotate(-45deg)';
        // Show sidebar burger, hide top burger
        topBurgerMenu.classList.add('hidden');
        sidebarBurgerMenu.classList.remove('hidden');
    } else {
        // Transform back to burger
        lines[0].style.transform = 'none';
        lines[1].style.opacity = '1';
        lines[2].style.transform = 'none';
        // Show top burger, hide sidebar burger
        topBurgerMenu.classList.remove('hidden');
        sidebarBurgerMenu.classList.add('hidden');
    }
}

function setInitialSidebarState() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    const isMobile = isMobileDevice();
    
    if (isMobile) {
        sidebar.style.transform = 'translateX(-100%)';
        mainContent.style.marginLeft = '0';
        toggleBurgerMenu(false);
    } else {
        sidebar.style.transform = 'translateX(0)';
        mainContent.style.marginLeft = '256px';
        toggleBurgerMenu(true);
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    
    if (sidebar.style.transform === 'translateX(-100%)') {
        sidebar.style.transform = 'translateX(0)';
        mainContent.style.marginLeft = '256px';
        toggleBurgerMenu(true);
    } else {
        sidebar.style.transform = 'translateX(-100%)';
        mainContent.style.marginLeft = '0';
        toggleBurgerMenu(false);
    }
}

// Set initial state on load
document.addEventListener('DOMContentLoaded', setInitialSidebarState);

// Update on resize
window.addEventListener('resize', setInitialSidebarState); 