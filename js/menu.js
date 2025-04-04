const hamburgerButton = document.getElementById('hamburgerButton');
const mobileMenu = document.getElementById('mobileMenu');
const closeButton = mobileMenu.querySelector('button'); // Select the close button inside the mobile menu

// Open the mobile menu when the hamburger button is clicked
hamburgerButton.addEventListener('click', () => {
  mobileMenu.classList.remove('hidden');
});

// Close the mobile menu when the close button is clicked
closeButton.addEventListener('click', () => {
  mobileMenu.classList.add('hidden');
});