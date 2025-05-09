function initializeMultiSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;

    // Check if already initialized
    if (select.parentNode && select.parentNode.classList.contains('multi-select-container')) {
        select.style.setProperty('display', 'none', 'important'); 
        return; 
    }

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
    
    // Function to update the display of selected items
    function updateDisplay() {
        const selectedOptions = Array.from(select.options).filter(opt => opt.selected);
        display.innerHTML = selectedOptions.length > 0 
            ? selectedOptions.map(opt => `<span class="multi-select-option">${opt.text}<button class="remove-item" data-value="${opt.value}">×</button></span>`).join('') + 
              '<button class="clear-all"><svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg></button>'
            : '<span class="placeholder">Select options...</span>';
            
        // Add click handler for the clear all button
        const clearAllBtn = display.querySelector('.clear-all');
        if (clearAllBtn) {
            clearAllBtn.onclick = (e) => {
                e.stopPropagation();  // Prevent dropdown from opening
                Array.from(select.options).forEach(option => option.selected = false);
                dropdown.querySelectorAll('.dropdown-option').forEach(option => {
                    option.classList.remove('selected');
                });
                updateDisplay();
                select.dispatchEvent(new Event('change'));
            };
        }
    }

    // Handle option selection
    dropdown.addEventListener('click', (e) => {
        const option = e.target.closest('.dropdown-option');
        if (!option) return;

        const value = option.dataset.value;
        // const text = option.textContent; // text is not used
        
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
        if (!e.target.classList.contains('remove-item') && !e.target.closest('.remove-item')) {
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
    
    // Hide the original select but keep it functional
    select.style.setProperty('display', 'none', 'important');
    
    // Update on change
    select.addEventListener('change', updateDisplay);
    updateDisplay();
}

function initializeSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;

    // Check if already initialized
    if (select.parentNode && select.parentNode.classList.contains('multi-select-container')) {
        select.style.setProperty('display', 'none', 'important');
        return;
    }

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
    select.style.setProperty('display', 'none', 'important');
    
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

// Initialize all selects in a container
function initializeAllSelects(container = document) {
    // Initialize multi-selects
    container.querySelectorAll('select.multiselect').forEach(select => {
        if (select.id) {
            initializeMultiSelect(select.id);
        }
    });
    
    // Initialize styled selects
    container.querySelectorAll('select.styled-select').forEach(select => {
        if (select.id) {
            initializeSelect(select.id);
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeAllSelects();
    
    // Re-initialize after HTMX content swaps
    document.body.addEventListener('htmx:afterSwap', (evt) => {
        initializeAllSelects(evt.detail.target); // Initialize any new custom selects
        
        // Observer for newly added select elements within the swapped content
        const newNodesObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) { // Element node
                            // Handle direct node if it's a select, or find selects within it
                            const newSelects = [];
                            if (node.matches('select.styled-select, select.multiselect')) {
                                newSelects.push(node);
                            } else {
                                node.querySelectorAll('select.styled-select, select.multiselect').forEach(s => newSelects.push(s));
                            }

                            newSelects.forEach(currentSelect => {
                                // Ensure it's hidden initially
                                currentSelect.style.setProperty('display', 'none', 'important');

                                // Attach a style monitor to this specific select
                                const styleChangeObserver = new MutationObserver((styleMutations) => {
                                    styleMutations.forEach((styleMutation) => {
                                        if (styleMutation.type === 'attributes' && styleMutation.attributeName === 'style') {
                                            if (styleMutation.target.style.display !== 'none') {
                                                styleMutation.target.style.setProperty('display', 'none', 'important');
                                            }
                                        }
                                    });
                                });
                                styleChangeObserver.observe(currentSelect, { attributes: true, attributeFilter: ['style'] });
                            });
                        }
                    });
                }
            });
        });
        newNodesObserver.observe(evt.detail.target, { childList: true, subtree: true });
    });
});

// Export functions for use in other files
window.initializeMultiSelect = initializeMultiSelect;
window.initializeSelect = initializeSelect;
window.initializeAllSelects = initializeAllSelects; 