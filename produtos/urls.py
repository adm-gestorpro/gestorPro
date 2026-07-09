from django.urls import path, include

from . import views

urlpatterns = [
    path('listar', views.listar_produtos, name='listar_produtos'),
    path('controle_validade', views.controle_validade, name='controle_validade'),
    path('cadastrar_validade', views.cadastrar_validade, name='cadastrar_validade'),
    path('editar_validade/<int:id>/', views.editar_validade, name='editar_validade'),
    path('inativar_validade/<int:id>/', views.inativar_validade, name='inativar_validade'),
    path('api/buscar-produtos/', views.api_buscar_produtos, name='api_buscar_produtos'),
]