from django.urls import path, include

from . import views

urlpatterns = [
    path('list', views.ticket_list, name='ticket_list'),
    path('create', views.ticket_create, name='ticket_create'),
    path('detail/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
]