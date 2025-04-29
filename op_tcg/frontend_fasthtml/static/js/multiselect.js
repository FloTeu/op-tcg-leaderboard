function initializeMultiSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;

    // Create container
    const container = document.createElement('div');
    container.className = 'multi-select-container';
    
    // Create label
    const label = document.createElement('label');
    label.className = 'multi-select-label';
    label.textContent = select.getAttribute('title') || select.getAttribute('label') || '';
    label.htmlFor = selectId;
    
    // Create display area
    const display = document.createElement('div');
    display.className = 'multi-select';
    
    // Create search input
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'multi-select-search';
    searchInput.placeholder = 'Search options...';
    
    // Create dropdown
    const dropdown = document.createElement('div');
    dropdown.className = 'multi-select-dropdown';
    
    // Copy options to dropdown
    Array.from(select.options).forEach(option => {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'dropdown-option';
        optionDiv.textContent = option.text;
        optionDiv.dataset.value = option.value;
        if (option.selected) {
            optionDiv.classList.add('selected');
        }
        dropdown.appendChild(optionDiv);
    });
    
    // Create clear all button
    const clearAll = document.createElement('button');
    clearAll.className = 'clear-all';
    clearAll.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>';
    clearAll.onclick = () => {
        Array.from(select.options).forEach(option => option.selected = false);
        dropdown.querySelectorAll('.dropdown-option').forEach(option => {
            option.classList.remove('selected');
        });
        updateDisplay();
        select.dispatchEvent(new Event('change'));
    };

    // Function to update the display of selected items
    function updateDisplay() {
        const selectedOptions = Array.from(select.options).filter(opt => opt.selected);
        display.innerHTML = selectedOptions.length > 0 
            ? selectedOptions.map(opt => `<span class="multi-select-option">${opt.text}<button class="remove-item" data-value="${opt.value}">×</button></span>`).join('')
            : '<span class="placeholder">Select options...</span>';
    }

    // Handle option selection
    dropdown.addEventListener('click', (e) => {
        const option = e.target.closest('.dropdown-option');
        if (!option) return;

        const value = option.dataset.value;
        const text = option.textContent;
        
        // Toggle selection
        const selectOption = Array.from(select.options).find(o => o.value === value);
        if (selectOption) {
            selectOption.selected = !selectOption.selected;
            option.classList.toggle('selected');
        }
        
        updateDisplay();
        select.dispatchEvent(new Event('change'));
    });

    // Handle removing items from display
    display.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-item')) {
            const value = e.target.dataset.value;
            const option = Array.from(select.options).find(opt => opt.value === value);
            if (option) {
                option.selected = false;
                const dropdownOption = dropdown.querySelector(`.dropdown-option[data-value="${value}"]`);
                if (dropdownOption) {
                    dropdownOption.classList.remove('selected');
                }
            }
            updateDisplay();
            select.dispatchEvent(new Event('change'));
        }
    });

    // Show/hide dropdown on click
    display.addEventListener('click', (e) => {
        if (!e.target.classList.contains('remove-item')) {
            dropdown.classList.toggle('show');
            searchInput.classList.toggle('show');
            if (dropdown.classList.contains('show')) {
                searchInput.focus();
            }
        }
    });

    // Handle search input
    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        Array.from(dropdown.querySelectorAll('.dropdown-option')).forEach(option => {
            const isVisible = option.textContent.toLowerCase().includes(searchTerm);
            option.style.display = isVisible ? '' : 'none';
        });
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
    container.appendChild(label);
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

function initializeSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;

    // Create container
    const container = document.createElement('div');
    container.className = 'multi-select-container';
    
    // Create label
    const label = document.createElement('label');
    label.className = 'multi-select-label';
    label.textContent = select.getAttribute('title') || select.getAttribute('label') || '';
    label.htmlFor = selectId;
    
    // Create display area
    const display = document.createElement('div');
    display.className = 'multi-select';
    
    // Create search input
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'multi-select-search';
    searchInput.placeholder = 'Search options...';
    
    // Create dropdown
    const dropdown = document.createElement('div');
    dropdown.className = 'multi-select-dropdown';
    
    // Copy options to dropdown
    Array.from(select.options).forEach(option => {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'dropdown-option';
        optionDiv.textContent = option.text;
        optionDiv.dataset.value = option.value;
        if (option.selected) {
            optionDiv.classList.add('selected');
            display.textContent = option.text;
        }
        dropdown.appendChild(optionDiv);
    });
    
    // Function to update the display
    function updateDisplay(selectedText) {
        display.textContent = selectedText || 'Select an option...';
    }

    // Handle option selection
    dropdown.addEventListener('click', (e) => {
        const option = e.target.closest('.dropdown-option');
        if (!option) return;

        const value = option.dataset.value;
        const text = option.textContent;
        
        // Update original select
        Array.from(select.options).forEach(opt => opt.selected = false);
        const selectOption = Array.from(select.options).find(o => o.value === value);
        if (selectOption) {
            selectOption.selected = true;
        }

        // Update UI
        dropdown.querySelectorAll('.dropdown-option').forEach(opt => opt.classList.remove('selected'));
        option.classList.add('selected');
        updateDisplay(text);
        
        // Close dropdown
        dropdown.classList.remove('show');
        searchInput.classList.remove('show');
        
        // Trigger change event
        select.dispatchEvent(new Event('change'));
    });

    // Show/hide dropdown on click
    display.addEventListener('click', () => {
        dropdown.classList.toggle('show');
        searchInput.classList.toggle('show');
        if (searchInput.classList.contains('show')) {
            searchInput.focus();
        }
    });

    // Handle search input
    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        Array.from(dropdown.querySelectorAll('.dropdown-option')).forEach(option => {
            const isVisible = option.textContent.toLowerCase().includes(searchTerm);
            option.style.display = isVisible ? '' : 'none';
        });
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
    container.appendChild(label);
    container.appendChild(display);
    container.appendChild(select);
    container.appendChild(searchInput);
    container.appendChild(dropdown);
    
    // Hide the original select but keep it functional
    select.style.display = 'none';
    
    // Update on change
    select.addEventListener('change', () => {
        const selectedOption = Array.from(select.options).find(opt => opt.selected);
        if (selectedOption) {
            updateDisplay(selectedOption.text);
            dropdown.querySelectorAll('.dropdown-option').forEach(opt => {
                opt.classList.toggle('selected', opt.dataset.value === selectedOption.value);
            });
        }
    });
    
    // Initial display update
    const selectedOption = Array.from(select.options).find(opt => opt.selected);
    updateDisplay(selectedOption ? selectedOption.text : 'Select an option...');
}

// Initialize all multi-selects and normal selects on page load
document.addEventListener('DOMContentLoaded', () => {
    // Initialize multi-selects
    initializeMultiSelect('release-meta-formats-select');
    
    // Initialize normal selects with class 'styled-select'
    document.querySelectorAll('select.styled-select').forEach(select => {
        initializeSelect(select.id);
    });
}); 