
// Function to transform HTML node to an object
export function extractObjectFromLegendHtml(node: HTMLElement): Record<string, number> {
    /**
    Example: {
        "Enel (Y)": 67.2,
        "Rob Lucci (B)": 63.9,
        "Monkey.D.Luffy (BY)": 60,
        "Monkey.D.Luffy (B)": 59.2,
        "Jewelry Bonney (G)": 53.5
    }
    returns Data inside of legend
    */
    const table = node.querySelector('table');
    if (!table) {
        return {}; // Return an empty object if there's no table
    }

    const result: Record<string, number> = {};

    // Iterate over each row in the table
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 3) { // Ensure there are at least three cells
            const name = cells[1].textContent?.trim() || ''; // Get the name from the second cell
            const value = parseFloat(cells[2].textContent?.trim() || '0'); // Get the value from the third cell
            result[name] = value; // Add to the result object
        }
    });

    return result; // Return the resulting object
}


// Function to update HTML table values based on legendData
export function updateLegendHtmlValues(node: HTMLElement, legendData: Record<string, number>): void {
    const table = node.querySelector('table');
    if (!table) {
        console.warn('No table found in the provided node.');
        return; // Exit if there's no table
    }

    // Iterate over each row in the table
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 3) { // Ensure there are at least three cells
            const name = cells[1].textContent?.trim() || ''; // Get the name from the second cell

            // Update the value in the third cell if the name exists in legendData
            if (legendData.hasOwnProperty(name)) {
                cells[2].textContent = legendData[name].toString(); // Update the cell with the corresponding value
            }
        }
    });
}