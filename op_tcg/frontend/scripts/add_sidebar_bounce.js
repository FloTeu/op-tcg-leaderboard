// Select the element with the specific data-testid attribute
const match = parent.document.querySelector('[data-testid="stSidebarCollapsedControl"]');
if (match) {
    match.classList.add("bounce");
} else {
    console.error('Element with data-testid="stSidebarCollapsedControl" not found.');
}