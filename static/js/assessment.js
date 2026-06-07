'use strict';
// Assessment form – multi-section navigation, live preview, API, factor chart

let currentSection = 1;
let factorChartInstance = null;

// ── Section navigation ──────────────────────────────────────────────────────
function nextSection(num) {
  if (num > currentSection && !validateSection(currentSection)) return;
  var prev = document.getElementById('section' + currentSection);
  var next = document.getElementById('section' + num);
  if (!prev || !next) return;
  prev.classList.add('d-none');
  next.classList.remove('d-none');
  currentSection = num;
  updateProgress();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function validateSection(num) {
  var section = document.getElementById('section' + num);
  if (!section) return true;
  var inputs = section.querySelectorAll('[required]');
  var valid = true;
  inputs.forEach(function(inp) {
    inp.classList.remove('is-invalid');
    if (!inp.value.trim()) {
      inp.classList.add('is-invalid');
      valid = false;
    }
  });
  if (!valid) {
    var first = section.querySelector('.is-invalid');
    if (first) first.focus();
  }
  return valid;
}

function updateProgress() {
  // Update step indicators
  for (var i = 1; i <= 3; i++) {
    var s = document.getElementById('step' + i);
    if (!s) continue;
    s.classList.remove('active', 'done');
    if (i === currentSection) s.classList.add('active');
    else if (i < currentSection) s.classList.add('done');
  }
}

// ── Live preview ─────────────────────────────────────────────────────────
function updateLivePreview() {
  function gv(id) {
    var el = document.getElementById(id);
    return el ? el.value : '';
  }
  var age    = parseFloat(gv('driver_age'))         || 35;
  var exp    = parseFloat(gv('driving_experience'))  || 5;
  var acc    = parseFloat(gv('previous_accidents'))  || 0;
  var viol   = parseFloat(gv('traffic_violations'))  || 0;
  var night  = parseFloat(gv('night_driving_pct'))   || 20;
  var miles  = parseFloat(gv('annual_mileage'))      || 15000;
  var credit = parseFloat(gv('credit_score'))        || 680;
  var vtype  = gv('vehicle_type')    || 'sedan';
  var loc    = gv('primary_location') || 'suburban';

  var score = 20;
  if (age < 25)      score += (25 - age) * 1.8;
  else if (age > 65) score += (age - 65) * 1.2;
  if (exp < 2)       score += 18;
  else if (exp < 5)  score += 10;
  else if (exp < 10) score += 4;
  score += acc * 14 + viol * 5;
  score += (miles - 3000) / 52000 * 10;
  score += night * 0.12;
  var vtMap = { sedan:0, van:0, suv:3, truck:4, sports:12, motorcycle:18 };
  score += vtMap[vtype] || 0;
  var lcMap = { suburban:0, rural:2, highway:4, urban:7 };
  score += lcMap[loc] || 0;
  score += Math.max(0, (700 - credit) / 40);
  score = Math.round(Math.min(Math.max(score, 0), 100));

  var cat = score < 26 ? 'Low' : score < 51 ? 'Medium' : score < 76 ? 'High' : 'Very High';
  var badgeMap = {
    'Low':      { cls:'bg-success',           bar:'bg-success'  },
    'Medium':   { cls:'bg-warning text-dark',  bar:'bg-warning'  },
    'High':     { cls:'bg-danger',             bar:'bg-danger'   },
    'Very High':{ cls:'bg-danger',             bar:'bg-danger'   }
  };
  var c = badgeMap[cat] || badgeMap['Medium'];

  var barEl   = document.getElementById('liveBar');
  var badgeEl = document.getElementById('liveCategoryBadge');
  var scoreEl = document.getElementById('liveScore');
  if (barEl)   { barEl.style.width = score + '%'; barEl.className = 'progress-bar ' + c.bar; }
  if (badgeEl) { badgeEl.className = 'badge fs-6 px-3 py-2 ' + c.cls; badgeEl.textContent = cat + ' Risk'; }
  if (scoreEl) scoreEl.textContent = score;
}

// ── Submit ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  updateLivePreview();

  var form = document.getElementById('assessmentForm');
  if (!form) return;

  form.addEventListener('submit', function(e) {
    e.preventDefault();
    if (!validateSection(3)) return;

    var btn = document.getElementById('submitBtn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Calculating…'; }

    var payload = {
      driver_age:         parseInt(document.getElementById('driver_age').value, 10),
      driving_experience: parseInt(document.getElementById('driving_experience').value, 10),
      gender:             document.getElementById('gender').value,
      marital_status:     document.getElementById('marital_status').value,
      credit_score:       parseInt(document.getElementById('credit_score').value, 10),
      vehicle_type:       document.getElementById('vehicle_type').value,
      vehicle_age:        parseInt(document.getElementById('vehicle_age').value, 10),
      annual_mileage:     parseInt(document.getElementById('annual_mileage').value, 10),
      primary_location:   document.getElementById('primary_location').value,
      previous_accidents: parseInt(document.getElementById('previous_accidents').value, 10),
      traffic_violations: parseInt(document.getElementById('traffic_violations').value, 10),
      night_driving_pct:  parseInt(document.getElementById('night_driving_pct').value, 10)
    };

    // Show modal with spinner
    var modalEl = document.getElementById('resultModal');
    var modal;
    try {
      modal = new bootstrap.Modal(modalEl);
      modal.show();
    } catch(err) {
      console.error('Modal error:', err);
    }

    fetch('/api/assess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(function(resp) { return resp.json(); })
    .then(function(data) {
      if (data.error) {
        renderError(data.error);
      } else {
        renderResult(data);
        var viewBtn = document.getElementById('viewReportBtn');
        if (viewBtn && data.assessment_id) viewBtn.href = '/report/' + data.assessment_id;
      }
    })
    .catch(function(err) {
      renderError('Network error: ' + err.message);
    })
    .finally(function() {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-cpu me-2"></i>Calculate Risk Score'; }
    });
  });
});

// ── Colors ───────────────────────────────────────────────────────────────
var COLOR_MAP = {
  'Low':      { header:'#10b981', badge:'rg-badge-low',      bar:'bg-success'  },
  'Medium':   { header:'#f59e0b', badge:'rg-badge-medium',   bar:'bg-warning'  },
  'High':     { header:'#ef4444', badge:'rg-badge-high',     bar:'bg-danger'   },
  'Very High':{ header:'#7c3aed', badge:'rg-badge-very-high',bar:'bg-danger'   }
};

// ── Render result ─────────────────────────────────────────────────────────
function renderResult(data) {
  var cat = data.risk_category;
  var c   = COLOR_MAP[cat] || COLOR_MAP['Medium'];

  var header = document.getElementById('resultModalHeader');
  if (header) {
    header.style.background = 'linear-gradient(135deg,' + c.header + ',#0d1b2a)';
  }

  // Probabilities mini bars
  var probsHtml = '';
  if (data.class_probabilities) {
    Object.keys(data.class_probabilities).forEach(function(cls) {
      var p   = data.class_probabilities[cls];
      var pct = Math.round(p * 100);
      var cm  = COLOR_MAP[cls] || { bar:'bg-secondary' };
      probsHtml += '<div class="d-flex align-items-center gap-2 mb-1">' +
        '<span class="small" style="min-width:78px;">' + cls + '</span>' +
        '<div class="progress flex-grow-1" style="height:8px;border-radius:4px;">' +
          '<div class="progress-bar ' + cm.bar + '" style="width:' + pct + '%;transition:width 1s ease;"></div>' +
        '</div>' +
        '<span class="small fw-bold" style="min-width:36px;">' + pct + '%</span></div>';
    });
  }

  // Recommendations
  var recsHtml = '';
  if (data.recommendations && data.recommendations.length) {
    recsHtml = '<hr><h6 class="fw-semibold mb-2"><i class="bi bi-lightbulb-fill me-1 text-warning"></i>Recommendations</h6>' +
      '<ul class="ps-0 mb-0" style="list-style:none;">';
    data.recommendations.forEach(function(r) {
      recsHtml += '<li class="mb-2 d-flex gap-2 align-items-start small">' +
        '<i class="bi bi-check-circle-fill text-success mt-1 flex-shrink-0"></i>' +
        '<span>' + r + '</span></li>';
    });
    recsHtml += '</ul>';
  }

  var body = document.getElementById('resultModalBody');
  if (!body) return;

  body.innerHTML =
    // Gauge + KPIs row
    '<div class="row align-items-center g-3 mb-3">' +
      '<div class="col-md-4 text-center">' +
        '<div id="resultGauge" class="d-inline-block"></div>' +
        '<div class="mt-1"><span class="badge px-3 py-2 ' + c.badge + ' fs-6">' + cat + ' Risk</span></div>' +
      '</div>' +
      '<div class="col-md-8">' +
        '<div class="row g-2 text-center mb-3">' +
          '<div class="col-4"><div class="p-2 rounded-3 h-100" style="background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.2);">' +
            '<div class="fw-bold fs-4 text-primary">' + data.premium_multiplier + '\xd7</div>' +
            '<div class="small text-muted">Premium<br>Multiplier</div></div></div>' +
          '<div class="col-4"><div class="p-2 rounded-3 h-100" style="background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.2);">' +
            '<div class="fw-bold fs-4 text-warning">' + Math.round(data.claim_probability * 100) + '%</div>' +
            '<div class="small text-muted">Claim<br>Probability</div></div></div>' +
          '<div class="col-4"><div class="p-2 rounded-3 h-100" style="background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.2);">' +
            '<div class="fw-bold fs-4 text-success">' + data.risk_score + '</div>' +
            '<div class="small text-muted">Risk<br>Score</div></div></div>' +
        '</div>' +
        '<div class="mb-1 small fw-semibold text-muted text-uppercase" style="letter-spacing:.06em;">Class Probabilities</div>' +
        probsHtml +
      '</div>' +
    '</div>' +
    '<hr>' +
    '<h6 class="fw-semibold mb-2"><i class="bi bi-bar-chart-steps me-1 text-warning"></i>Risk Factor Contributions</h6>' +
    '<canvas id="factorContribChart" style="max-height:220px;"></canvas>' +
    recsHtml;

  // ── Radar chart HTML ──
  body.innerHTML += '<hr><h6 class="fw-semibold mb-2"><i class="bi bi-hexagon me-1 text-info"></i>Driver Risk Profile (Radar)</h6>' +
    '<canvas id="radarChart" style="max-height:260px;"></canvas>';

  // Draw gauge + factor chart + radar after DOM settles
  var factors = data.factor_contributions || [];
  setTimeout(function() {
    if (typeof drawGauge === 'function') drawGauge('resultGauge', data.risk_score, data.risk_category);
    drawFactorChart(factors);
    drawRadarChart(data);
    // Konfetti for Low Risk!
    if (data.risk_category === 'Low' && typeof confetti === 'function') {
      confetti({ particleCount: 180, spread: 80, origin: { y: 0.5 },
        colors: ['#ff9f0a','#10b981','#3b82f6','#7c3aed','#f87171'] });
      setTimeout(() => confetti({ particleCount: 80, angle: 60, spread: 55, origin: { x: 0 } }), 400);
      setTimeout(() => confetti({ particleCount: 80, angle: 120, spread: 55, origin: { x: 1 } }), 600);
    }
  }, 200);
}

function drawFactorChart(factors) {
  if (factorChartInstance) {
    try { factorChartInstance.destroy(); } catch(e) {}
    factorChartInstance = null;
  }
  var canvas = document.getElementById('factorContribChart');
  if (!canvas || !factors.length) return;

  // Check Chart.js loaded
  if (typeof Chart === 'undefined') {
    canvas.parentElement.innerHTML = '<p class="text-muted small">Chart.js not loaded (check internet connection)</p>';
    return;
  }

  var top    = factors.slice(0, 10);
  var labels = top.map(function(f) { return f.factor; });
  var values = top.map(function(f) { return f.value; });
  var colors = top.map(function(f) { return f.type === 'risk' ? 'rgba(220,53,69,.8)' : 'rgba(25,135,84,.8)'; });

  try {
    factorChartInstance = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{ label: 'Impact (pts)', data: values, backgroundColor: colors, borderRadius: 6 }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: function(ctx) { return ' ' + ctx.parsed.x.toFixed(1) + ' pts'; } } }
        },
        scales: {
          x: { beginAtZero: true, grid: { color: '#f0f0f0' }, title: { display: true, text: 'Impact (points)' } },
          y: { grid: { display: false }, ticks: { font: { size: 11 } } }
        }
      }
    });
  } catch(err) {
    console.error('Factor chart error:', err);
  }
}

var radarInstance = null;
function drawRadarChart(data) {
  if (radarInstance) { try { radarInstance.destroy(); } catch(e){} radarInstance = null; }
  var canvas = document.getElementById('radarChart');
  if (!canvas || typeof Chart === 'undefined') return;

  // Normalize each factor to 0-100 scale for radar
  var age = data.risk_score; // placeholder values based on risk factors
  var vals = [
    Math.min(100, (data.claim_probability || 0) * 100),
    Math.min(100, (data.premium_multiplier - 1) / 1.3 * 100),
    Math.min(100, data.risk_score),
    Math.min(100, ((data.factor_contributions || []).filter(f=>f.type==='risk').reduce((a,b)=>a+b.value,0))/50*100),
    Math.min(100, 100 - (data.confidence || 85)),
    Math.min(100, data.risk_score * 0.8)
  ];

  try {
    radarInstance = new Chart(canvas, {
      type: 'radar',
      data: {
        labels: ['Claim Risk','Premium Level','Overall Score','Risk Factors','Uncertainty','Profile Risk'],
        datasets: [{
          label: 'Driver Profile',
          data: vals,
          backgroundColor: 'rgba(255,159,10,.15)',
          borderColor: '#ff9f0a',
          borderWidth: 2.5,
          pointBackgroundColor: '#ff9f0a',
          pointRadius: 4,
        }]
      },
      options: {
        responsive: true,
        scales: { r: {
          beginAtZero: true, max: 100,
          grid: { color: 'rgba(0,0,0,.06)' },
          pointLabels: { font: { size: 11 }, color: '#64748b' },
          ticks: { display: false }
        }},
        plugins: { legend: { display: false } }
      }
    });
  } catch(e) {}
}

function renderError(msg) {
  var body = document.getElementById('resultModalBody');
  if (body) body.innerHTML = '<div class="alert alert-danger m-3"><i class="bi bi-exclamation-triangle me-2"></i>' + msg + '</div>';
}
