"""
URL configuration for gestorPro project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.defaults import permission_denied

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('controle.urls')),
    path('compras/', include('compras.urls')),
    path('produtos/', include('produtos.urls')),
    path('fornecedores/', include('fornecedores.urls')),
    path('notify/', include('notify.urls')),
    path('tickets/', include('tickets.urls')),

    path('error403/', lambda r: permission_denied(r, Exception("Teste de erro 403"))),
]

handler403 = views.erro_403_customizado
