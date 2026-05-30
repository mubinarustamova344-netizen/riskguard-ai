'use strict';
// Dashboard – Chart.js charts with robust error handling

var RISK_COLORS = {
  'Low':'#198754', 'Medium':'#fd7e14', 'High':'#e05a00', 'Very High':'#dc3545'
};
var charts = {};

function destroyChart(id) {
  if (charts[id]) { try { charts[id].destroy(); } catch(e){} delete charts[id]; }
}

function safeCtx(canvasId) {
  var el = document.getElementById(canvasId);
  if (!el) return null;
  try { return el.getContext('2d'); } catch(e) { return null; }
}

function loadAllCharts() {
  if (typeof Chart === 'undefined') {
    showChartError('Chart.js not loaded. Check internet connection or CDN access.');
    return;
  }

  Promise.all([
    fetch('/api/stats').then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; }),
    fetch('/api/model-metrics').then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; }),
    fetch('/api/age-distribution').then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; }),
    fetch('/api/score-distribution').then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; })
  ]).then(function(results) {
    var stats     = results[0];
    var metrics   = results[1];
    var ageDist   = results[2];
    var scoreDist = results[3];

    if (stats && stats.total > 0) {
      var cd = stats.category_distribution || {};
      setStat('statLow',    cd['Low']        || 0);
      setStat('statMedium', cd['Medium']     || 0);
      setStat('statHigh',   cd['High']       || 0);
      setStat('statVH',     cd['Very High']  || 0);
      drawRiskDist(cd);
      drawVehicleChart(stats.vehicle_type_distribution || {});
      drawLocationChart(stats.location_distribution || {});
      drawMonthly(stats.monthly_assessments || {});
      drawLiveStatsDetail(stats);
    } else {
      setStat('statLow', 0); setStat('statMedium', 0);
      setStat('statHigh', 0); setStat('statVH', 0);
      drawEmptyCanvas('riskDistChart');
      drawEmptyCanvas('vehicleRiskChart');
      drawEmptyCanvas('locationRiskChart');
      drawEmptyCanvas('monthlyChart');
      drawNoData('liveStatsDetail');
    }

    if (ageDist)   drawAgeDist(ageDist);
    else           drawEmptyCanvas('ageDistChart');

    if (scoreDist) drawScoreDist(scoreDist);
    else           drawEmptyCanvas('scoreDistChart');

    if (metrics) {
      drawFeatureImportance(metrics.feature_importance || {});
      drawModelCompare(metrics.all_results || {});
    } else {
      drawEmptyCanvas('featureImportanceChart');
      drawEmptyCanvas('modelCompareChart');
    }
  }).catch(function(err) {
    console.error('Dashboard load error:', err);
    showChartError('Failed to load dashboard data: ' + err.message);
  });
}

function setStat(id, val) {
  var el = document.getElementById(id);
  if (el) el.textContent = val;
}

function drawEmptyCanvas(id) {
  var ctx = safeCtx(id);
  if (!ctx) return;
  var el = document.getElementById(id);
  ctx.clearRect(0, 0, el.width, el.height);
  ctx.font = '13px Segoe UI, sans-serif';
  ctx.fillStyle = '#adb5bd';
  ctx.textAlign = 'center';
  ctx.fillText('No data yet – run an assessment first', el.width / 2, 60);
}

function drawNoData(id) {
  var el = document.getElementById(id);
  if (el) el.innerHTML = '<p class="text-muted text-center py-3">No assessments yet. <a href="/assessment">Start one!</a></p>';
}

function showChartError(msg) {
  ['riskDistChart','vehicleRiskChart','ageDistChart','scoreDistChart',
   'locationRiskChart','monthlyChart','featureImportanceChart','modelCompareChart']
  .forEach(function(id) {
    var ctx = safeCtx(id);
    if (!ctx) return;
    var el = document.getElementById(id);
    ctx.clearRect(0, 0, el.width, el.height);
    ctx.font = '12px Segoe UI, sans-serif';
    ctx.fillStyle = '#dc3545';
    ctx.textAlign = 'center';
    ctx.fillText(msg, el.width / 2, 40);
  });
}

// ── Risk Distribution Donut ────────────────────────────────────────────────
function drawRiskDist(dist) {
  destroyChart('riskDist');
  var ctx = safeCtx('riskDistChart');
  if (!ctx) return;
  var labels = Object.keys(dist);
  if (!labels.length) { drawEmptyCanvas('riskDistChart'); return; }
  charts['riskDist'] = new Chart(ctx, {
    type: 'doughnut',
    data: { labels: labels, datasets: [{
      data: labels.map(function(l){ return dist[l]; }),
      backgroundColor: labels.map(function(l){ return RISK_COLORS[l] || '#888'; }),
      borderWidth: 3, borderColor: '#fff', hoverOffset: 10
    }]},
    options: {
      responsive: true, maintainAspectRatio: true, cutout: '60%',
      plugins: {
        legend: { position: 'bottom', labels: { padding: 14, font: { size: 12 } } },
        tooltip: { callbacks: { label: function(c){ return ' ' + c.label + ': ' + c.parsed + ' assessments'; } } }
      }
    }
  });
}

// ── Vehicle Bar ────────────────────────────────────────────────────────────
function drawVehicleChart(vtypes) {
  destroyChart('vehicleRisk');
  var ctx = safeCtx('vehicleRiskChart');
  if (!ctx) return;
  var labels = Object.keys(vtypes).map(function(v){ return v.charAt(0).toUpperCase() + v.slice(1); });
  var data   = Object.values(vtypes);
  var bgColors = ['#4a90d9','#198754','#dc3545','#fd7e14','#6f42c1','#20c997'];
  charts['vehicleRisk'] = new Chart(ctx, {
    type:'bar',
    data:{ labels:labels, datasets:[{ label:'Assessments', data:data, backgroundColor:bgColors.slice(0,data.length), borderRadius:8 }]},
    options:{ responsive:true, plugins:{ legend:{ display:false }}, scales:{ y:{ beginAtZero:true, grid:{ color:'#f0f0f0' }}, x:{ grid:{ display:false }}}}
  });
}

// ── Age Distribution ───────────────────────────────────────────────────────
function drawAgeDist(dist) {
  destroyChart('ageDist');
  var ctx = safeCtx('ageDistChart');
  if (!ctx) return;
  var labels = Object.keys(dist);
  var data   = Object.values(dist);
  charts['ageDist'] = new Chart(ctx, {
    type:'bar',
    data:{ labels:labels, datasets:[{ label:'Assessments', data:data,
      backgroundColor:['#dc3545','#fd7e14','#198754','#198754','#fd7e14','#dc3545'].slice(0,data.length),
      borderRadius:8 }]},
    options:{ responsive:true, plugins:{ legend:{ display:false }},
              scales:{ y:{ beginAtZero:true, grid:{ color:'#f0f0f0' }}, x:{ grid:{ display:false }}}}
  });
}

// ── Score Distribution ─────────────────────────────────────────────────────
function drawScoreDist(dist) {
  destroyChart('scoreDist');
  var ctx = safeCtx('scoreDistChart');
  if (!ctx) return;
  var labels = Object.keys(dist);
  var data   = Object.values(dist);
  charts['scoreDist'] = new Chart(ctx, {
    type:'bar',
    data:{ labels:labels, datasets:[{ label:'Assessments', data:data,
      backgroundColor:['#198754','#a3e635','#fd7e14','#e05a00','#dc3545'].slice(0,data.length),
      borderRadius:8 }]},
    options:{ responsive:true, plugins:{ legend:{ display:false }},
              scales:{ y:{ beginAtZero:true, grid:{ color:'#f0f0f0' }}, x:{ grid:{ display:false }}}}
  });
}

// ── Location Bar ───────────────────────────────────────────────────────────
function drawLocationChart(dist) {
  destroyChart('locationRisk');
  var ctx = safeCtx('locationRiskChart');
  if (!ctx) return;
  var labels = Object.keys(dist).map(function(l){ return l.charAt(0).toUpperCase() + l.slice(1); });
  charts['locationRisk'] = new Chart(ctx, {
    type:'bar',
    data:{ labels:labels, datasets:[{ label:'Assessments', data:Object.values(dist), backgroundColor:'#4a90d9', borderRadius:8 }]},
    options:{ responsive:true, plugins:{ legend:{ display:false }},
              scales:{ y:{ beginAtZero:true, grid:{ color:'#f0f0f0' }}, x:{ grid:{ display:false }}}}
  });
}

// ── Monthly Trend ──────────────────────────────────────────────────────────
function drawMonthly(monthly) {
  destroyChart('monthly');
  var ctx = safeCtx('monthlyChart');
  if (!ctx) return;
  var sorted = Object.keys(monthly).sort();
  charts['monthly'] = new Chart(ctx, {
    type:'line',
    data:{ labels:sorted, datasets:[{ label:'Assessments', data:sorted.map(function(k){ return monthly[k]; }),
      borderColor:'#4a90d9', backgroundColor:'rgba(74,144,217,.12)',
      tension:0.4, pointRadius:5, pointBackgroundColor:'#4a90d9', fill:true }]},
    options:{ responsive:true, plugins:{ legend:{ display:false }},
              scales:{ y:{ beginAtZero:true, grid:{ color:'#f0f0f0' }}, x:{ grid:{ display:false }}}}
  });
}

// ── Feature Importance ─────────────────────────────────────────────────────
function drawFeatureImportance(imp) {
  destroyChart('featureImp');
  var ctx = safeCtx('featureImportanceChart');
  if (!ctx) return;
  var entries = Object.entries(imp).slice(0, 12);
  if (!entries.length) { drawEmptyCanvas('featureImportanceChart'); return; }
  var labels = entries.map(function(e){ return e[0].replace(/num__|cat__/g,'').replace(/_/g,' '); });
  var values = entries.map(function(e){ return parseFloat((e[1] * 100).toFixed(2)); });
  charts['featureImp'] = new Chart(ctx, {
    type:'bar',
    data:{ labels:labels, datasets:[{ label:'Importance (%)', data:values,
      backgroundColor:values.map(function(_,i){ return 'hsla(' + (210 - i*14) + ',70%,50%,.85)'; }),
      borderRadius:6 }]},
    options:{ indexAxis:'y', responsive:true,
      plugins:{ legend:{ display:false }},
      scales:{ x:{ beginAtZero:true, grid:{ color:'#f0f0f0' }, title:{ display:true, text:'Importance (%)' }},
               y:{ grid:{ display:false }, ticks:{ font:{ size:11 }}}}}
  });
}

// ── Model Accuracy Comparison ──────────────────────────────────────────────
function drawModelCompare(allResults) {
  destroyChart('modelCompare');
  var ctx = safeCtx('modelCompareChart');
  if (!ctx) return;
  var names = Object.keys(allResults);
  if (!names.length) { drawEmptyCanvas('modelCompareChart'); return; }
  var accs = names.map(function(n){ return parseFloat((allResults[n].accuracy * 100).toFixed(2)); });
  var cvs  = names.map(function(n){ return parseFloat((allResults[n].cv_accuracy * 100).toFixed(2)); });
  charts['modelCompare'] = new Chart(ctx, {
    type:'bar',
    data:{ labels:names,
      datasets:[
        { label:'Test Accuracy (%)', data:accs, backgroundColor:'#4a90d9', borderRadius:6 },
        { label:'CV Accuracy (%)',   data:cvs,  backgroundColor:'#198754', borderRadius:6 }
      ]},
    options:{ responsive:true,
      plugins:{ legend:{ position:'bottom', labels:{ font:{ size:11 }}}},
      scales:{ y:{ min:50, max:100, grid:{ color:'#f0f0f0' }}, x:{ grid:{ display:false }}}}
  });
}

// ── Stats Detail ───────────────────────────────────────────────────────────
function drawLiveStatsDetail(stats) {
  var el = document.getElementById('liveStatsDetail');
  if (!el) return;
  el.innerHTML =
    '<div class="row g-3 text-center">' +
      '<div class="col-6"><div class="p-3 bg-light rounded-3"><div class="fw-bold fs-3 text-primary">' + stats.total + '</div><div class="small text-muted">Total Assessments</div></div></div>' +
      '<div class="col-6"><div class="p-3 bg-light rounded-3"><div class="fw-bold fs-3 text-warning">' + stats.avg_risk_score + '</div><div class="small text-muted">Avg Risk Score</div></div></div>' +
      '<div class="col-6"><div class="p-3 bg-light rounded-3"><div class="fw-bold fs-3 text-success">' + stats.min_risk_score + '</div><div class="small text-muted">Lowest Score</div></div></div>' +
      '<div class="col-6"><div class="p-3 bg-light rounded-3"><div class="fw-bold fs-3 text-danger">' + stats.max_risk_score + '</div><div class="small text-muted">Highest Score</div></div></div>' +
    '</div>';
}

document.addEventListener('DOMContentLoaded', loadAllCharts);
