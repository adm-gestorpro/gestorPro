// firebase-messaging-sw.js

// Importa os scripts do Firebase (usando a versão de compatibilidade para rodar no SW)
importScripts('https://www.gstatic.com/firebasejs/10.8.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.8.1/firebase-messaging-compat.js');

// Configuração do seu projeto no Firebase (Pegue isso no Firebase Console > Configurações do Projeto)
const firebaseConfig = {
    apiKey: "SUA_API_KEY",
    authDomain: "seu-projeto.firebaseapp.com",
    projectId: "seu-projeto",
    storageBucket: "seu-projeto.appspot.com",
    messagingSenderId: "SEU_SENDER_ID",
    appId: "SEU_APP_ID"
};

// Inicializa o Firebase no Service Worker
firebase.initializeApp(firebaseConfig);

// Inicializa o Messaging
const messaging = firebase.messaging();

// (Opcional) Captura a notificação em segundo plano se quiser customizar a exibição
messaging.onBackgroundMessage((payload) => {
    console.log('[firebase-messaging-sw.js] Notificação recebida em background ', payload);
    
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: '/static/img/icone-gestorpro.png', // Caminho para o ícone do seu sistema
        data: payload.data // Passa os dados extras, como a URL
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});

// Ação ao clicar na notificação (abrir o link do chamado)
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    if (event.notification.data && event.notification.data.url) {
        event.waitUntil(
            clients.openWindow(event.notification.data.url)
        );
    }
});