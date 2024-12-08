// Function to find the index of the equivalent object in data
export function findEquivalentIndex(data: Array<Record<string, number>>, element: Record<string, number>): number | null {
    // Iterate over the data array
    for (let i = 0; i < data.length; i++) {
        const dataItem = data[i];

        // Check if the current dataItem matches the element
        const keysMatch = Object.keys(element).every(key => dataItem[key] === element[key]);

        // If a match is found, return the index
        if (keysMatch && Object.keys(dataItem).length === Object.keys(element).length) {
            return i; // Return the index
        }
    }

    // Return null if no equivalent index is found
    return null;
}