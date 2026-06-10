from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='has_any_group')
def has_any_group(user, group_names):
    """
    Verifica se o usuário pertence a pelo menos um dos grupos fornecidos.
    Os grupos devem ser passados separados por vírgula. Ex: "Gerentes,Diretores"
    """
    if not user.is_authenticated:
        return False
    
    # Transforma a string "Gerentes,Diretores" em uma lista ['Gerentes', 'Diretores']
    # O strip() remove espaços extras caso você digite "Gerentes, Diretores"
    groups_list = [g.strip() for g in group_names.split(',')]
    
    # Verifica se o usuário está em algum dos grupos da lista
    return user.groups.filter(name__in=groups_list).exists()