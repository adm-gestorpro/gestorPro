from django.urls import path
from . import views

app_name = 'notify'

urlpatterns = [
    path('fcm/registrar/', views.registrar_dispositivo_fcm, name='fcm_registrar'),
    # No futuro, você pode colocar aqui:
    # path('listar/', views.listar_notificacoes, name='listar'),
    # path('<int:pk>/marcar-lida/', views.marcar_lida, name='marcar_lida'),
]