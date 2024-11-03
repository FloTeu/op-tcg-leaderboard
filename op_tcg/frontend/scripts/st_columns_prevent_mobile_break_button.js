// Tries to fix https://github.com/streamlit/streamlit/issues/5003

// Select all elements with the data-testid="column" attribute
const columns = parent.document.querySelectorAll('[data-testid="column"]');

//document.addEventListener('DOMContentLoaded', () => {
// Use setTimeout to delay the execution slightly
setTimeout(() => {
    // Iterate over each column element
    columns.forEach((column, index) => {
        // Check if the column contains an element with the class 'stButton'
        const hasButton = column.querySelector('.stButton');

        // Check if the previous column has a button
        const previousColumn = columns[index - 1];
        const previousHasButton = previousColumn && previousColumn.querySelector('.stButton');

        // Check if the next column has a button
        const nextColumn = columns[index + 1];
        const nextHasButton = nextColumn && nextColumn.querySelector('.stButton');

        // If the column has a button or if it has a neighbor with a button, set min-width
        if (hasButton || previousHasButton || nextHasButton) {
            // Get the computed style for the current column
            const computedStyle = window.getComputedStyle(column);
            // Change min width
            column.style.minWidth = computedStyle.flexBasis; // Set new min-width
        }
    });
}, 10); // Delay of 10 milliseconds
//});

