from django.urls import path, include

from . import views

urlpatterns = [
    path('conciliacao', views.conciliacao, name='conciliacao'),
    path('comparativo', views.ProdutoComparativoView.as_view(), name='comparativo'),
]