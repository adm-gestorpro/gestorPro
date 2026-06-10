from django.urls import path, include

from . import views

urlpatterns = [
    path('listar', views.listar_fornecedores, name='listar_fornecedores'),
]