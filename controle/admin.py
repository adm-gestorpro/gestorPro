from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import PerfilUsuario

class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    filter_horizontal = ('redes', 'lojas', 'vendedor')
    extra = 0 
    max_num = 1

class UserAdmin(BaseUserAdmin):
    inlines = (PerfilUsuarioInline,)
    
    # Define as colunas explicitamente
    list_display = ('username', 'email', 'first_name', 'is_staff', 'exibir_redes', 'exibir_lojas', 'exibir_vendedor')

    @admin.display(description='Redes')
    def exibir_redes(self, obj):
        # Tenta buscar usando o modelo diretamente para não errar o related_name
        perfil = PerfilUsuario.objects.filter(user=obj).first()
        if perfil and perfil.redes.exists():
            # O str(item) força o Django a usar o método __str__ do seu modelo Rede
            return ", ".join([str(item.cod_rede) for item in perfil.redes.all()])
        return "Sem Perfil cadastrado" if not perfil else "Sem Rede(s) cadastrada(s)"

    @admin.display(description='Lojas')
    def exibir_lojas(self, obj):
        perfil = PerfilUsuario.objects.filter(user=obj).first()
        if perfil and perfil.lojas.exists():
            return ", ".join([str(item.cod_loja) for item in perfil.lojas.all()])
        return "Sem Perfil cadastrado" if not perfil else "Sem Loja(s) cadastrada(s)"

    @admin.display(description='Vendedores')
    def exibir_vendedor(self, obj):
        perfil = PerfilUsuario.objects.filter(user=obj).first()
        if perfil and perfil.vendedor.exists():
            return ", ".join([str(item.cod_vendedor) for item in perfil.vendedor.all()])
        return "Sem Perfil cadastrado" if not perfil else "Sem Vendedor(es) cadastrada(s)"

admin.site.unregister(User)
admin.site.register(User, UserAdmin)