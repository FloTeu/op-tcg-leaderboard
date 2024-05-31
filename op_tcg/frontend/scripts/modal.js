// Get the modal
var modal = document.getElementById("myModal");

// Get the image and insert it inside the modal
function openModal(imgElement) {
  var modalImg = document.getElementById("img01");
  modal.style.display = "block";
  modalImg.src = imgElement.querySelector('img').src;
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