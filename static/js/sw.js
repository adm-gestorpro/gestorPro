const CACHE_NAME = 'gestorpro-v1';

// Evento de instalação
self.addEventListener('install', event => {
    self.skipWaiting(); // Garante que a nova versão do SW assuma o controle imediatamente
});

// Evento de ativação
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.filter(cacheName => cacheName !== CACHE_NAME)
                    .map(cacheName => caches.delete(cacheName))
            );
        })
    );
});

// Evento de fetch (onde a mágica acontece)
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // 1. IGNORAR LOGIN: Se for a página de login, sempre vai para a rede.
    // Isso evita que o formulário com token CSRF antigo seja servido do cache.
    if (url.pathname.includes('/login/')) {
        return; 
    }

    // 2. ESTRATÉGIA NETWORK-FIRST PARA HTML:
    // Tenta buscar o HTML da rede primeiro (para garantir tokens CSRF frescos).
    // Se estiver offline, serve o cache.
    if (event.request.headers.get('accept').includes('text/html')) {
        event.respondWith(
            fetch(event.request)
                .catch(() => caches.match(event.request))
        );
        return;
    }

    // 3. ESTRATÉGIA CACHE-FIRST PARA OUTROS ARQUIVOS (CSS, JS, Imagens):
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request);
        })
    );
});