const CACHE = 'riskguard-v1';
const ASSETS = [
  '/', '/assessment', '/history', '/chatbot', '/dashboard',
  '/static/css/style.css', '/static/css/premium.css',
  '/static/js/main.js', '/static/js/assessment.js',
  '/static/js/chatbot.js', '/static/js/dashboard.js',
  '/static/img/favicon.svg', '/static/img/logo.svg'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS).catch(() => {})));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (e.request.url.includes('/api/')) return;
  e.respondWith(
    fetch(e.request).then(res => {
      const clone = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, clone));
      return res;
    }).catch(() => caches.match(e.request))
  );
});
