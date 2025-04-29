function initializeMultiSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;

    // Create container
    const container = document.createElement('div');
    container.className = 'multi-select-container';
    
    // Create display area
    const display = document.createElement('div');
    display.className = 'multi-select';
    
    // Create search input
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'multi-select-search';
    searchInput.placeholder = 'Search options...';
    
    // Create dropdown
    const dropdown = document.createElement('select');
    dropdown.className = 'multi-select-dropdown';
    dropdown.multiple = true;
    dropdown.size = 5;
    
    // Copy options to dropdown
    Array.from(select.options).forEach(option => {
        const newOption = document.createElement('option');
        newOption.value = option.value;
        newOption.textContent = option.text;
        newOption.selected = option.selected;
        dropdown.appendChild(newOption);
    });
    
    // Create clear all button
    const clearAll = document.createElement('button');
    clearAll.className = 'clear-all';
    clearAll.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>';
    clearAll.onclick = () => {
        Array.from(select.options).forEach(option => option.selected = false);
        Array.from(dropdown.options).forEach(option => option.selected = false);
        updateDisplay();
        select.dispatchEvent(new Event('change'));
    };
    
    // Function to filter options based on search
    function filterOptions(searchText) {
        const options = Array.from(dropdown.options);
        options.forEach(option => {
            const text = option.textContent.toLowerCase();
            const search = searchText.toLowerCase();
            option.style.display = text.includes(search) ? '' : 'none';
        });
    }
    
    // Add search input event listener
    searchInput.addEventListener('input', (e) => {
        filterOptions(e.target.value);
    });
    
    // Function to update the display
    function updateDisplay() {
        display.innerHTML = '';
        const selectedOptions = Array.from(select.selectedOptions);
        
        if (selectedOptions.length === 0) {
            const placeholder = document.createElement('span');
            placeholder.textContent = 'Select options...';
            placeholder.style.color = 'rgb(156, 163, 175)';
            display.appendChild(placeholder);
        } else {
            selectedOptions.forEach(option => {
                const optionDiv = document.createElement('div');
                optionDiv.className = 'multi-select-option';
                
                const textSpan = document.createElement('span');
                textSpan.textContent = option.text;
                
                const removeButton = document.createElement('button');
                removeButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>';
                removeButton.onclick = (e) => {
                    e.stopPropagation();
                    option.selected = false;
                    const dropdownOption = Array.from(dropdown.options).find(o => o.value === option.value);
                    if (dropdownOption) dropdownOption.selected = false;
                    updateDisplay();
                    select.dispatchEvent(new Event('change'));
                };
                
                optionDiv.appendChild(textSpan);
                optionDiv.appendChild(removeButton);
                display.appendChild(optionDiv);
            });
        }
    }

    // Handle dropdown changes
    dropdown.addEventListener('change', (e) => {
        // Get the last changed option
        const changedOption = e.target.options[e.target.selectedIndex];
        if (changedOption) {
            // Only add the selection if it's not already selected
            if (changedOption.selected) {
                const selectOption = Array.from(select.options).find(o => o.value === changedOption.value);
                if (selectOption && !selectOption.selected) {
                    selectOption.selected = true;
                }
            }
        }
        updateDisplay();
        select.dispatchEvent(new Event('change'));
    });

    // Show/hide dropdown on click
    display.addEventListener('click', () => {
        dropdown.classList.toggle('show');
        searchInput.classList.toggle('show');
        if (dropdown.classList.contains('show')) {
            searchInput.focus();
        }
    });

    // Hide dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
            dropdown.classList.remove('show');
            searchInput.classList.remove('show');
        }
    });
    
    // Initialize
    select.parentNode.insertBefore(container, select);
    container.appendChild(display);
    container.appendChild(select);
    container.appendChild(searchInput);
    container.appendChild(dropdown);
    container.appendChild(clearAll);
    
    // Hide the original select but keep it functional
    select.style.display = 'none';
    
    // Update on change
    select.addEventListener('change', updateDisplay);
    updateDisplay();
}

// Initialize all multi-selects on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeMultiSelect('release-meta-formats-select');
}); 