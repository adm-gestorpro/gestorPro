const CACHE_NAME = 'gestorpro-v1';
// Cache apenas arquivos locais essenciais
const urlsToCache = [
  '/',
  '/static/manifest.json' 
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});

