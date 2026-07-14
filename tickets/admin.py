from django.contrib import admin
from .models import Department, TicketSubject

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    # Campos que aparecerão na lista de departamentos
    list_display = ('name', 'id') 
    
    # Campo de busca para encontrar departamentos rapidamente
    search_fields = ('name',)
    
    # Ordenação padrão
    ordering = ('name',)


@admin.register(TicketSubject)
class TicketSubjectAdmin(admin.ModelAdmin):
    # Facilita ver quem é filho de quem
    list_display = ('name', 'department', 'parent')
    
    # Filtros úteis para encontrar categorias rapidamente
    list_filter = ('department', 'parent')
    
    # Busca por nome
    search_fields = ('name',)