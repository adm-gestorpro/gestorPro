from django.urls import path, include
from django.contrib.staticfiles.views import serve

from . import views

urlpatterns = [
    path('', views.login_view, name='login_view'),
    path('logout_view', views.logout_view, name='logout_view'),
    path('logout', views.logout_user, name='logout_user'),
    path('pedido/', views.pedido, name="pedido"),
    path('atualizacoes/', views.atualizacoes, name='atualizacoes'),
    path('atualizar_redes', views.atualizar_redes, name='atualizar_redes'),
    path('atualizar_lojas', views.atualizar_lojas, name='atualizar_lojas'),
    path('atualizar_produtos', views.atualizar_produtos, name='atualizar_produtos'),
    path('atualizar_clientes', views.atualizar_clientes, name='atualizar_clientes'),
    path('atualizar_fornecedores', views.atualizar_fornecedores, name='atualizar_fornecedores'),
    path('atualizar_vendedores', views.atualizar_vendedores, name='atualizar_vendedores'),
    path('atualizar_venda_online', views.atualizar_venda_online, name='atualizar_venda_online'),
    path('atualizar_pedido_balcao', views.atualizar_pedido_balcao, name='atualizar_pedido_balcao'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('agenda', views.agenda, name='agenda'),

    path('sw.js', serve, {'path': 'js/sw.js'}),
]