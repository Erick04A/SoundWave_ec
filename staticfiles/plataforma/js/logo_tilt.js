document.addEventListener('DOMContentLoaded', function () {
  const logo = document.getElementById('hero-logo-tilt');
  if (!logo) return;

  const hero = document.querySelector('.hero-container');
  if (!hero) return;

  let ticking = false;
  let mouseX = 0;
  let mouseY = 0;
  let isHovered = false;

  const MAX_ROTATION = 12;
  const DETECTION_RADIUS = 300;

  logo.style.transition = 'transform 0.4s ease-out, filter 0.3s ease';

  function onMouseMove(e) {
    mouseX = e.clientX;
    mouseY = e.clientY;

    const rect = logo.getBoundingClientRect();
    const logoX = rect.left + rect.width / 2;
    const logoY = rect.top + rect.height / 2;

    const dx = mouseX - logoX;
    const dy = mouseY - logoY;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance < DETECTION_RADIUS) {
      if (!isHovered) {
        isHovered = true;
        logo.style.transition = 'transform 0.15s ease-out, filter 0.3s ease';
      }
      if (!ticking) {
        requestAnimationFrame(updateTilt);
        ticking = true;
      }
    } else {
      if (isHovered) {
        resetTilt();
      }
    }
  }

  function onMouseLeave() {
    if (isHovered) {
      resetTilt();
    }
  }

  function updateTilt() {
    const rect = logo.getBoundingClientRect();
    const logoX = rect.left + rect.width / 2;
    const logoY = rect.top + rect.height / 2;

    const dx = mouseX - logoX;
    const dy = mouseY - logoY;

    const percentX = Math.max(-1, Math.min(1, dx / DETECTION_RADIUS));
    const percentY = Math.max(-1, Math.min(1, dy / DETECTION_RADIUS));

    const rotateX = -percentY * MAX_ROTATION;
    const rotateY = percentX * MAX_ROTATION;

    logo.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;

    const shadowX = -percentX * 10;
    const shadowY = -percentY * 10;

    const img = logo.querySelector('.hero-logo-img');
    if (img) {
      img.style.filter = `brightness(0) invert(1) sepia(1) saturate(3.5) hue-rotate(10deg) brightness(1.05) drop-shadow(${shadowX}px ${shadowY}px 12px rgba(184, 146, 63, 0.45)) drop-shadow(${shadowX / 2}px ${(shadowY / 2) + 2}px 6px rgba(0, 0, 0, 0.4))`;
    }

    ticking = false;
  }

  function resetTilt() {
    isHovered = false;
    logo.style.transition = 'transform 0.4s ease-out, filter 0.3s ease';
    logo.style.transform = 'perspective(800px) rotateX(0deg) rotateY(0deg)';

    const img = logo.querySelector('.hero-logo-img');
    if (img) {
      img.style.filter = 'brightness(0) invert(1) sepia(1) saturate(3.5) hue-rotate(10deg) brightness(1.05) drop-shadow(0 0 12px rgba(184, 146, 63, 0.45)) drop-shadow(0 2px 6px rgba(0, 0, 0, 0.4))';
    }
  }

  window.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mouseleave', onMouseLeave);
});
