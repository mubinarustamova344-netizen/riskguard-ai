'use strict';
// main.js — Global: dark mode, toasts, counter animation, gauge, scroll animations

// ── Dark Mode ─────────────────────────────────────────────────
(function() {
  var saved = localStorage.getItem('rg-theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
  document.body.setAttribute('data-theme', saved);
})();

function toggleDarkMode() {
  var current = document.body.getAttribute('data-theme') || 'light';
  var next = current === 'dark' ? 'light' : 'dark';
  document.body.setAttribute('data-theme', next);
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('rg-theme', next);
  var icon = document.getElementById('darkModeIcon');
  if (icon) icon.className = next === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
}

document.addEventListener('DOMContentLoaded', function() {
  var saved = localStorage.getItem('rg-theme') || 'light';
  var icon = document.getElementById('darkModeIcon');
  if (icon) icon.className = saved === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
});

// ── Toast Notifications ───────────────────────────────────────
function showToast(message, type, duration) {
  type = type || 'info';
  duration = duration || 3500;

  var icons = { success:'bi-check-circle-fill', warning:'bi-exclamation-triangle-fill',
                error:'bi-x-circle-fill', info:'bi-info-circle-fill' };
  var colors = { success:'var(--low)', warning:'var(--medium)',
                 error:'var(--high)', info:'#3b82f6' };

  var container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
  }

  var toast = document.createElement('div');
  toast.className = 'rg-toast ' + type + ' p-3 mb-2';
  toast.style.cursor = 'pointer';
  toast.innerHTML =
    '<div class="d-flex align-items-center gap-2">' +
      '<i class="bi ' + (icons[type]||'bi-info-circle-fill') + '" style="color:' + colors[type] + ';font-size:1.1rem;"></i>' +
      '<span class="flex-grow-1 small fw-500">' + message + '</span>' +
      '<button type="button" class="btn-close btn-close-sm" onclick="this.closest(\'.rg-toast\').remove()"></button>' +
    '</div>';

  container.appendChild(toast);
  toast.addEventListener('click', function() { toast.remove(); });

  setTimeout(function() {
    toast.style.transition = 'opacity .3s, transform .3s';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    setTimeout(function() { toast.remove(); }, 300);
  }, duration);
}

// ── Animated Counters ─────────────────────────────────────────
function animateCounter(el, target, duration, suffix) {
  suffix = suffix || '';
  var start = 0;
  var startTime = null;
  var isFloat = String(target).includes('.');
  var decimals = isFloat ? String(target).split('.')[1].length : 0;

  function step(timestamp) {
    if (!startTime) startTime = timestamp;
    var progress = Math.min((timestamp - startTime) / duration, 1);
    var eased = 1 - Math.pow(1 - progress, 3);
    var current = start + (target - start) * eased;
    el.textContent = (isFloat ? current.toFixed(decimals) : Math.round(current)) + suffix;
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = target + suffix;
  }
  requestAnimationFrame(step);
}

function initCounters() {
  var els = document.querySelectorAll('[data-counter]');
  if (!els.length) return;

  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        var el = entry.target;
        var target = parseFloat(el.getAttribute('data-counter'));
        var duration = parseInt(el.getAttribute('data-duration') || '1500');
        var suffix = el.getAttribute('data-suffix') || '';
        animateCounter(el, target, duration, suffix);
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.5 });

  els.forEach(function(el) { observer.observe(el); });
}

// ── Risk Gauge (SVG animated arc) ────────────────────────────
function drawGauge(canvasId, score, category) {
  var wrap = document.getElementById(canvasId);
  if (!wrap) return;

  var colors = { 'Low':'#10b981', 'Medium':'#f59e0b', 'High':'#ef4444', 'Very High':'#7c3aed' };
  var color = colors[category] || '#3b82f6';

  // Full arc circumference for a 85px radius semicircle
  var r = 85;
  var C = Math.PI * r; // half circumference ≈ 266.9
  var offset = C - (score / 100) * C;

  wrap.innerHTML =
    '<svg viewBox="0 0 200 115" style="width:100%;max-width:280px;">' +
      '<defs>' +
        '<linearGradient id="gaugeGrad_' + canvasId + '" x1="0%" y1="0%" x2="100%" y2="0%">' +
          '<stop offset="0%" stop-color="#10b981"/>' +
          '<stop offset="40%" stop-color="#f59e0b"/>' +
          '<stop offset="70%" stop-color="#ef4444"/>' +
          '<stop offset="100%" stop-color="#7c3aed"/>' +
        '</linearGradient>' +
      '</defs>' +
      // Background arc
      '<path d="M 15,110 A 85,85 0 0 1 185,110" fill="none" stroke="#e5e7eb" stroke-width="14" stroke-linecap="round"/>' +
      // Animated fill arc
      '<path id="gaugeArc_' + canvasId + '"' +
           ' d="M 15,110 A 85,85 0 0 1 185,110"' +
           ' fill="none" stroke="' + color + '" stroke-width="14" stroke-linecap="round"' +
           ' stroke-dasharray="' + C.toFixed(1) + '"' +
           ' stroke-dashoffset="' + C.toFixed(1) + '">' +
        '<animate attributeName="stroke-dashoffset"' +
                 ' from="' + C.toFixed(1) + '" to="' + offset.toFixed(1) + '"' +
                 ' dur="1.2s" calcMode="spline"' +
                 ' keySplines="0.4 0 0.2 1"' +
                 ' fill="freeze"/>' +
      '</path>' +
      // Score text
      '<text x="100" y="95" text-anchor="middle" font-family="Segoe UI,sans-serif"' +
           ' font-size="28" font-weight="800" fill="' + color + '">' + score + '</text>' +
      '<text x="100" y="112" text-anchor="middle" font-family="Segoe UI,sans-serif"' +
           ' font-size="9" fill="#94a3b8" letter-spacing="1.5">RISK SCORE</text>' +
    '</svg>';
}

// ── Scroll Reveal ─────────────────────────────────────────────
function initScrollReveal() {
  var els = document.querySelectorAll('.reveal-on-scroll');
  if (!els.length) return;

  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  els.forEach(function(el) { observer.observe(el); });
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  initCounters();
  initScrollReveal();

  // Navbar scroll shadow
  var navbar = document.querySelector('.rg-navbar');
  if (navbar) {
    window.addEventListener('scroll', function() {
      if (window.scrollY > 10) {
        navbar.style.boxShadow = '0 4px 24px rgba(0,0,0,.4)';
      } else {
        navbar.style.boxShadow = '0 2px 20px rgba(0,0,0,.3)';
      }
    });
  }
});
