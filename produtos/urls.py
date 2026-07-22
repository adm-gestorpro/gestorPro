from django.urls import path, include

from . import views

urlpatterns = [
    path('listar', views.listar_produtos, name='listar_produtos'),
    path('controle_validade', views.controle_validade, name='controle_validade'),
    path('cadastrar_validade', views.cadastrar_validade, name='cadastrar_validade'),
    path('editar_validade/<int:id>/', views.editar_validade, name='editar_validade'),
    path('inativar_validade/<int:id>/', views.inativar_validade, name='inativar_validade'),
    path('api/buscar-produtos/', views.api_buscar_produtos, name='api_buscar_produtos'),

    path('rupturas/', views.ruptura_list, name='ruptura_list'),
    path('rupturas/cadastrar/', views.cadastrar_ruptura, name='cadastrar_ruptura'),
    path('rupturas/buscar-produtos/', views.buscar_produtos_ajax, name='buscar_produtos_ajax'),
    path('rupturas/atualizar-status/', views.atualizar_status_ruptura, name='atualizar_status_ruptura'),
]