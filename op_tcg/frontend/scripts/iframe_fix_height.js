/*
Why do we need this script?
Context: Streamlit suggests to use components.html in order to include a iframe block (ink. css, html an js)
This iframes need a initial height in order to be visible to the user. However, we cannot know the height always as it might be changed dynamically.
Therefore, we need to change the height to the real content dynamically afterwards.
*/

function resizeIframes() {
    // Get all iframes on the page
    const iframes = parent.document.getElementsByTagName('iframe');
    // Loop through each iframe
    for (let i = 0; i < iframes.length; i++) {
        const iframe = iframes[i];

        // Check if the iframe is loaded and accessible
        try {
            // Get the document of the iframe
            const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;

            // Set the height of the iframe based on its content
            iframe.style.height = iframeDocument.body.scrollHeight + 'px';
        } catch (e) {
            // console.warn("Unable to access iframe:", iframe.src, e);
        }
    }
}

// Optional: Add event listener to resize iframes when the window is resized
// window.addEventListener('resize', resizeIframes);

// Set an interval to resize iframes every 1 seconds (1000 milliseconds)
setInterval(resizeIframes, 1000);