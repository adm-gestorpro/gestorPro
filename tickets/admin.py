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
    # 1. Trocamos 'department' por 'get_departments' (a função que criaremos abaixo)
    list_display = ('name', 'get_departments', 'parent')
    
    # 2. No list_filter, você pode manter 'department' (ou 'departments') 
    # pois o Django Admin sabe lidar com M2M para filtros automaticamente.
    list_filter = ('department', 'parent') 
    
    # Busca por nome
    search_fields = ('name',)

    # Função para exibir os departamentos de forma legível
    def get_departments(self, obj):
        # Pega todos os nomes dos departamentos relacionados e une com vírgula
        return ", ".join([dept.name for dept in obj.department.all()])
    
    # Define o título da coluna na tabela do Admin
    get_departments.short_description = 'Departamentos'