const columns = document.querySelectorAll('[data-testid="column"]');

// Iterate over each column element
columns.forEach(column => {
    // Get the computed style of the element
    const computedStyle = window.getComputedStyle(column);

    // Extract the flex-basis value
    const flexBasis = computedStyle.flexBasis;

    // Set the new min-width style
    column.style.setProperty('min-width', flexBasis, 'important');
});
