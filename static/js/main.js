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

// ── Risk Gauge (SVG animated speedometer) ────────────────────
function drawGauge(canvasId, score, category) {
  var wrap = document.getElementById(canvasId);
  if (!wrap) return;

  var colors = { 'Low':'#10b981', 'Medium':'#f59e0b', 'High':'#ef4444', 'Very High':'#7c3aed' };
  var glows  = { 'Low':'rgba(16,185,129,.45)', 'Medium':'rgba(245,158,11,.45)', 'High':'rgba(239,68,68,.45)', 'Very High':'rgba(124,58,237,.45)' };
  var color  = colors[category] || '#3b82f6';
  var glow   = glows[category]  || 'rgba(59,130,246,.4)';

  var r = 82;
  var C = Math.PI * r;
  var offset = C - (score / 100) * C;
  var id = 'g_' + canvasId;

  wrap.innerHTML =
    '<svg viewBox="0 0 200 118" style="width:100%;max-width:290px;overflow:visible;">' +
      '<defs>' +
        '<linearGradient id="bgGrad_' + id + '" x1="0%" y1="0%" x2="100%" y2="0%">' +
          '<stop offset="0%" stop-color="#10b981" stop-opacity=".25"/>' +
          '<stop offset="35%" stop-color="#f59e0b" stop-opacity=".25"/>' +
          '<stop offset="70%" stop-color="#ef4444" stop-opacity=".25"/>' +
          '<stop offset="100%" stop-color="#7c3aed" stop-opacity=".25"/>' +
        '</linearGradient>' +
        '<linearGradient id="fillGrad_' + id + '" x1="0%" y1="0%" x2="100%" y2="0%">' +
          '<stop offset="0%" stop-color="#10b981"/>' +
          '<stop offset="40%" stop-color="#f59e0b"/>' +
          '<stop offset="70%" stop-color="#ef4444"/>' +
          '<stop offset="100%" stop-color="#7c3aed"/>' +
        '</linearGradient>' +
        '<filter id="glow_' + id + '">' +
          '<feGaussianBlur stdDeviation="3" result="blur"/>' +
          '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>' +
        '</filter>' +
      '</defs>' +
      // Outer decorative ring
      '<circle cx="100" cy="110" r="95" fill="none" stroke="rgba(255,255,255,.04)" stroke-width="1"/>' +
      // Tick marks
      [0,20,40,60,80,100].map(function(v) {
        var angle = Math.PI * (1 - v/100);
        var x1 = 100 + 78 * Math.cos(angle), y1 = 110 - 78 * Math.sin(angle);
        var x2 = 100 + 88 * Math.cos(angle), y2 = 110 - 88 * Math.sin(angle);
        return '<line x1="' + x1.toFixed(1) + '" y1="' + y1.toFixed(1) + '" x2="' + x2.toFixed(1) + '" y2="' + y2.toFixed(1) + '" stroke="rgba(255,255,255,.2)" stroke-width="1.5" stroke-linecap="round"/>';
      }).join('') +
      // Background arc (rainbow dim)
      '<path d="M 18,110 A 82,82 0 0 1 182,110" fill="none" stroke="url(#bgGrad_' + id + ')" stroke-width="16" stroke-linecap="round"/>' +
      // Shadow arc
      '<path d="M 18,110 A 82,82 0 0 1 182,110" fill="none" stroke="' + glow + '" stroke-width="20" stroke-linecap="round" opacity=".18"' +
           ' stroke-dasharray="' + C.toFixed(1) + '" stroke-dashoffset="' + offset.toFixed(1) + '"/>' +
      // Animated fill arc
      '<path d="M 18,110 A 82,82 0 0 1 182,110" fill="none" stroke="url(#fillGrad_' + id + ')" stroke-width="16" stroke-linecap="round"' +
           ' filter="url(#glow_' + id + ')"' +
           ' stroke-dasharray="' + C.toFixed(1) + '" stroke-dashoffset="' + C.toFixed(1) + '">' +
        '<animate attributeName="stroke-dashoffset" from="' + C.toFixed(1) + '" to="' + offset.toFixed(1) + '"' +
                 ' dur="1.4s" calcMode="spline" keySplines="0.4 0 0.2 1" fill="freeze"/>' +
      '</path>' +
      // Needle dot
      '<circle cx="100" cy="110" r="7" fill="' + color + '" filter="url(#glow_' + id + ')" opacity="0">' +
        '<animate attributeName="opacity" from="0" to="1" begin="0.8s" dur=".4s" fill="freeze"/>' +
      '</circle>' +
      '<circle cx="100" cy="110" r="3.5" fill="#fff" opacity="0">' +
        '<animate attributeName="opacity" from="0" to="1" begin="0.8s" dur=".4s" fill="freeze"/>' +
      '</circle>' +
      // Zone labels
      '<text x="22" y="108" text-anchor="middle" font-family="Inter,sans-serif" font-size="7.5" fill="#10b981" font-weight="600">LOW</text>' +
      '<text x="178" y="108" text-anchor="middle" font-family="Inter,sans-serif" font-size="7.5" fill="#7c3aed" font-weight="600">V.HI</text>' +
      // Score number
      '<text x="100" y="90" text-anchor="middle" font-family="Inter,Segoe UI,sans-serif" font-size="34" font-weight="900" fill="' + color + '" filter="url(#glow_' + id + ')">' + score + '</text>' +
      '<text x="100" y="104" text-anchor="middle" font-family="Inter,sans-serif" font-size="8" fill="#94a3b8" letter-spacing="2" font-weight="600">/ 100</text>' +
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

// ── Loading Screen ────────────────────────────────────────────
(function() {
  var loader = document.getElementById('pageLoader');
  var bar    = document.getElementById('loaderBar');
  var txt    = document.getElementById('loaderText');
  if (!loader) return;
  var msgs = ['Initializing ML model…', 'Loading risk engine…', 'Almost ready…'];
  var i = 0;
  var prog = 0;
  var iv = setInterval(function() {
    prog += Math.random() * 35 + 15;
    if (prog > 95) prog = 95;
    if (bar) bar.style.width = prog + '%';
    if (txt && msgs[i]) { txt.textContent = msgs[i]; i++; }
  }, 250);
  window.addEventListener('load', function() {
    clearInterval(iv);
    if (bar) bar.style.width = '100%';
    setTimeout(function() {
      loader.style.opacity = '0';
      setTimeout(function() { loader.style.display = 'none'; }, 500);
    }, 300);
  });
})();

// ── Onboarding Tour ───────────────────────────────────────────
var tourSteps = [
  { icon:'🛡️', title:'Welcome to RiskGuard AI!', desc:'The most advanced insurance risk assessment platform. Let me show you around in 30 seconds.', anchor:null },
  { icon:'📋', title:'Risk Assessment', desc:'Fill in 12 driver parameters and get an instant ML-powered risk score with personalised recommendations.', anchor:'.btn-warning' },
  { icon:'🎮', title:'What-If Simulator', desc:'Adjust sliders and see your risk score change in REAL TIME. Try it — it\'s incredible!', anchor:null },
  { icon:'🤖', title:'AI Chatbot (24/7)', desc:'Ask anything about insurance, premiums or risk factors. Powered by advanced NLP engine.', anchor:null },
  { icon:'📊', title:'Analytics Dashboard', desc:'8 interactive charts, live map, model performance metrics and real-time updates.', anchor:null },
  { icon:'🎓', title:"You're all set!", desc:'Explore the platform. Everything is designed for professional insurance underwriting. Good luck!', anchor:null },
];
var tourIdx = 0;

function startTour() {
  tourIdx = 0;
  showTourStep();
}

function showTourStep() {
  var step = tourSteps[tourIdx];
  if (!step) { endTour(); return; }
  var card = document.getElementById('tourCard');
  var overlay = document.getElementById('tourOverlay');
  if (!card || !overlay) return;
  document.getElementById('tourIcon').textContent = step.icon;
  document.getElementById('tourTitle').textContent = step.title;
  document.getElementById('tourDesc').textContent  = step.desc;
  document.getElementById('tourStep').textContent  = (tourIdx + 1) + ' / ' + tourSteps.length;
  overlay.style.display = 'block';
  card.style.display = 'block';
  // Center card
  card.style.top  = '50%';
  card.style.left = '50%';
  card.style.transform = 'translate(-50%,-50%)';
}

function nextTourStep() {
  tourIdx++;
  if (tourIdx >= tourSteps.length) { endTour(); return; }
  showTourStep();
}

function endTour() {
  document.getElementById('tourCard').style.display    = 'none';
  document.getElementById('tourOverlay').style.display = 'none';
  localStorage.setItem('rg-tour-done', '1');
}

// ── Notification Badge ─────────────────────────────────────────
function loadNotifications() {
  fetch('/api/notifications')
    .then(r => r.json())
    .then(d => {
      var badge = document.getElementById('notifBadge');
      if (!badge) return;
      if (d.high_pending > 0) {
        badge.textContent = d.high_pending > 9 ? '9+' : d.high_pending;
        badge.style.display = 'flex';
      } else {
        badge.style.display = 'none';
      }
    }).catch(() => {});
}

// ── PWA Service Worker ─────────────────────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/static/sw.js').catch(function() {});
  });
}

// ── Canvas Particle Network ───────────────────────────────────
function initParticles() {
  var hero = document.querySelector('.rg-hero');
  if (!hero) return;
  var canvas = document.createElement('canvas');
  canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;';
  hero.insertBefore(canvas, hero.firstChild);
  var ctx = canvas.getContext('2d');
  var pts = [], W, H, mx = -999, my = -999;

  function resize() {
    W = canvas.width = hero.offsetWidth;
    H = canvas.height = hero.offsetHeight;
  }
  resize();
  window.addEventListener('resize', function() { setTimeout(resize, 100); });
  hero.addEventListener('mousemove', function(e) {
    var r = hero.getBoundingClientRect();
    mx = e.clientX - r.left; my = e.clientY - r.top;
  });
  hero.addEventListener('mouseleave', function() { mx = -999; my = -999; });

  for (var i = 0; i < 60; i++) {
    pts.push({
      x: Math.random() * 1200, y: Math.random() * 500,
      vx: (Math.random() - .5) * .5, vy: (Math.random() - .5) * .5,
      r: Math.random() * 2.2 + .4, a: Math.random() * .45 + .1
    });
  }

  (function loop() {
    ctx.clearRect(0, 0, W, H);
    for (var i = 0; i < pts.length; i++) {
      var p = pts[i];
      var dx = mx - p.x, dy = my - p.y, d = Math.sqrt(dx*dx + dy*dy);
      if (d < 160 && d > 0) { p.vx += dx / d * .018; p.vy += dy / d * .018; }
      p.vx = Math.max(-1.3, Math.min(1.3, p.vx * .99));
      p.vy = Math.max(-1.3, Math.min(1.3, p.vy * .99));
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255,159,10,' + p.a + ')';
      ctx.fill();
    }
    for (var i = 0; i < pts.length; i++) {
      for (var j = i + 1; j < pts.length; j++) {
        var dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
        var dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < 130) {
          ctx.beginPath();
          ctx.moveTo(pts[i].x, pts[i].y);
          ctx.lineTo(pts[j].x, pts[j].y);
          ctx.strokeStyle = 'rgba(255,159,10,' + (.13 * (1 - dist / 130)) + ')';
          ctx.lineWidth = .6;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(loop);
  })();
}

// ── Cursor Glow ───────────────────────────────────────────────
function initCursorGlow() {
  var glow = document.createElement('div');
  glow.style.cssText = 'position:fixed;top:0;left:0;width:350px;height:350px;border-radius:50%;background:radial-gradient(circle,rgba(255,159,10,.065) 0%,transparent 70%);pointer-events:none;z-index:9990;will-change:left,top;transition:opacity .4s;';
  document.body.appendChild(glow);
  var tx = 0, ty = 0, cx = 0, cy = 0;
  document.addEventListener('mousemove', function(e) { tx = e.clientX; ty = e.clientY; });
  (function move() {
    cx += (tx - cx) * .1; cy += (ty - cy) * .1;
    glow.style.left = (cx - 175) + 'px';
    glow.style.top  = (cy - 175) + 'px';
    requestAnimationFrame(move);
  })();
}

// ── 3D Card Tilt ──────────────────────────────────────────────
function init3DTilt() {
  var sel = '.feature-card, .hero-stat-card, .step-card, .metric-card, .kpi-box';
  document.querySelectorAll(sel).forEach(function(card) {
    card.style.willChange = 'transform';
    card.addEventListener('mousemove', function(e) {
      var r = card.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width;
      var y = (e.clientY - r.top) / r.height;
      var rx = (y - .5) * 16;
      var ry = (.5 - x) * 16;
      card.style.transform = 'perspective(900px) rotateX(' + rx + 'deg) rotateY(' + ry + 'deg) translateY(-8px) scale(1.025)';
      card.style.transition = 'none';
    });
    card.addEventListener('mouseleave', function() {
      card.style.transform = '';
      card.style.transition = 'transform .5s cubic-bezier(.4,0,.2,1)';
    });
  });
}

// ── Magnetic Buttons ──────────────────────────────────────────
function initMagneticBtns() {
  document.querySelectorAll('.btn-warning.fw-bold, .btn-warning.btn-lg, .hero-actions .btn').forEach(function(btn) {
    btn.addEventListener('mousemove', function(e) {
      var r = btn.getBoundingClientRect();
      var x = (e.clientX - r.left - r.width / 2) * .22;
      var y = (e.clientY - r.top - r.height / 2) * .22;
      btn.style.transform = 'translate(' + x + 'px,' + y + 'px) translateY(-2px)';
    });
    btn.addEventListener('mouseleave', function() {
      btn.style.transform = '';
    });
  });
}

// ── Scroll Progress Bar ───────────────────────────────────────
function initScrollProgress() {
  var bar = document.createElement('div');
  bar.style.cssText = 'position:fixed;top:0;left:0;height:3px;background:linear-gradient(90deg,#ff9f0a,#00d4ff,#7c3aed);width:0%;z-index:99999;transition:width .1s;pointer-events:none;';
  document.body.appendChild(bar);
  window.addEventListener('scroll', function() {
    var pct = (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100;
    bar.style.width = Math.min(pct, 100) + '%';
  });
}

// ── Reveal on scroll with stagger ────────────────────────────
function initRevealStagger() {
  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry, i) {
      if (entry.isIntersecting) {
        setTimeout(function() {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }, i * 80);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.feature-card, .step-card, .hero-stat-card, .metric-card, .chart-card, .kpi-box, .stat-pill').forEach(function(el, i) {
    el.style.opacity = '0';
    el.style.transform = 'translateY(28px)';
    el.style.transition = 'opacity .6s ease, transform .6s ease';
    observer.observe(el);
  });
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  initCounters();
  initScrollReveal();
  loadNotifications();
  setInterval(loadNotifications, 60000);

  // Visual effects
  initParticles();
  initCursorGlow();
  setTimeout(init3DTilt, 300);
  initMagneticBtns();
  initScrollProgress();
  setTimeout(initRevealStagger, 100);

  // Show tour on first visit
  if (!localStorage.getItem('rg-tour-done') && !window.location.pathname.includes('login')) {
    setTimeout(startTour, 2800);
  }

  // Navbar scroll shadow
  var navbar = document.querySelector('.rg-navbar');
  if (navbar) {
    window.addEventListener('scroll', function() {
      if (window.scrollY > 10) {
        navbar.style.boxShadow = '0 4px 32px rgba(0,0,0,.5), 0 0 60px rgba(255,159,10,.04)';
        navbar.style.borderBottomColor = 'rgba(255,159,10,.22)';
      } else {
        navbar.style.boxShadow = '0 2px 20px rgba(0,0,0,.3)';
        navbar.style.borderBottomColor = 'rgba(255,255,255,.06)';
      }
    });
  }
});
