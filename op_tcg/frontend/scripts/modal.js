// Get the modal
var modal = document.getElementById("myModal");

// Get the image and insert it inside the modal
var currentIndex = 0; // To keep track of the current image
var images = []; // Array to hold the image sources
var isSwiping = false; // Flag to prevent skipping images

function openModal(imgElement) {
  var modalImg = document.getElementById("img01");
  modal.style.display = "block";
  modalImg.src = imgElement.querySelector('img').src;

  // Store current image index and all image sources
  currentIndex = parseInt(imgElement.dataset.index); // Assuming you add data-index to each image
  images = [...document.querySelectorAll('.item-image img')].map(img => img.src);
}

// Get the <span> element that closes the modal
function closeModal() {
  modal.style.display = "none";
}

// When the user clicks anywhere outside of the modal, close it
window.onclick = function(event) {
  if (event.target === modal) {
    closeModal();
  }
}

// Swipe functionality
let startX = 0;

modal.addEventListener('touchstart', function(event) {
  startX = event.touches[0].clientX; // Get the starting touch position
});

modal.addEventListener('touchmove', function(event) {
  if (isSwiping) return; // Prevent action if currently swiping

  let endX = event.touches[0].clientX; // Get the ending touch position
  let diffX = startX - endX;

  if (Math.abs(diffX) > 50) { // Threshold for swipe
    isSwiping = true; // Set flag to true to prevent further swipes

    if (diffX > 0) {
      nextImage(); // Swipe left
    } else {
      previousImage(); // Swipe right
    }

    setTimeout(() => {
      isSwiping = false; // Reset flag after a short delay
    }, 500); // Adjust delay as needed (500ms is a good starting point)
  }
});

// Function to show the next image
function nextImage() {
  currentIndex = (currentIndex + 1) % images.length; // Loop back to start
  document.getElementById("img01").src = images[currentIndex];
}

// Function to show the previous image
function previousImage() {
  currentIndex = (currentIndex - 1 + images.length) % images.length; // Loop back to end
  document.getElementById("img01").src = images[currentIndex];
}

// Click functionality for navigating images
document.getElementById("img01").addEventListener('click', function(event) {
  const imgWidth = this.clientWidth; // Get the width of the image
  const clickX = event.clientX - this.getBoundingClientRect().left; // Get the click position relative to the image

  if (clickX < imgWidth / 4) {
    previousImage(); // Clicked on the left 1/4
  } else if (clickX > (imgWidth * 3) / 4) {
    nextImage(); // Clicked on the right 1/4
  }
});
