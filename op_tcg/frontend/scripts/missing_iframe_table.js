// catches bug of missing content for st-elements library
function getAllIframes(doc) {
    const iframes = doc.querySelectorAll('iframe');
    let allIframes = Array.from(iframes); // Convert NodeList to Array

    // Loop through each iframe to find nested iframes
    allIframes.forEach(iframe => {
        try {
            const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;
            const nestedIframes = getAllIframes(iframeDocument); // Recursively get nested iframes
            allIframes = allIframes.concat(nestedIframes); // Combine arrays
        } catch (error) {
            console.warn('Cannot access nested iframe: ' + error);
            // Handle CORS issues gracefully
        }
    });

    return allIframes; // Return all found iframes
}

function isElementVisible(el) {
    // Check if the element is visible
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetWidth > 0 && el.offsetHeight > 0;
}

function checkIframeForTable() {
    const iframes = getAllIframes(parent.document); // Get all iframes from the parent document
    let tableFound = false;

    // Loop through each iframe using forEach
    iframes.forEach((iframe, index) => {
        try {
            const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;

            const table = iframeDocument.querySelector('table');
            // Check if there is a table in the iframe
            if (table) {
                console.log('Iframe at index ' + index + ' contains a table.');

                // Check if the table is visible
                if (isElementVisible(table)) {
                    console.log('Table in iframe at index ' + index + ' is visible to the user.');
                    tableFound = true; // Table found and is visible
                } else {
                    console.log('Table in iframe at index ' + index + ' is not visible to the user.');
                }
            }
        } catch (error) {
            console.warn('Cannot access iframe at index ' + index + ': ' + error);
            // This may happen if the iframe is from a different origin (CORS issue)
        }
    });

    return tableFound; // Return whether a table was found
}


// Use setTimeout to delay the execution slightly
setTimeout(() => {
    if (!checkIframeForTable()){
        // Show a warning message before reloading
        const userConfirmed = confirm('Leaderboard could not be loaded. Do you want to reload the page?');
        if (userConfirmed) {
            console.log('No iframe contains a table. Reloading the page...');
            parent.window.location.reload(); // Reload the page
        } else {
            console.log('Page reload canceled by the user.');
        }
    }
}, 3000); // Delay in milliseconds

