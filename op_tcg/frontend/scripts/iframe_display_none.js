

setTimeout(() => {
    // Select all elements with the class 'element-container'
    const containers = parent.document.querySelectorAll('.element-container');

    // Iterate through each container
    containers.forEach(container => {
        // Check if there is an iframe with height="0" inside the container
        const iframe = container.querySelector('iframe[height="0"]');

        // If such an iframe exists, hide the container
        if (iframe) {
            container.style.display = 'none';
        }
    });
}, 100); // Delay of 100 milliseconds
