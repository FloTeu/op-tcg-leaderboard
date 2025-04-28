// Sidebar functionality
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    const burgerMenu = document.getElementById('burger-menu');
    
    if (sidebar.style.transform === 'translateX(-100%)') {
        sidebar.style.transform = 'translateX(0)';
        mainContent.style.marginLeft = '256px';
        burgerMenu.style.left = 'auto';
        burgerMenu.style.right = '8px';
    } else {
        sidebar.style.transform = 'translateX(-100%)';
        mainContent.style.marginLeft = '0';
        burgerMenu.style.left = '8px';
        burgerMenu.style.right = 'auto';
    }
} 