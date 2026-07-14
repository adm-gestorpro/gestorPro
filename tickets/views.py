from django.shortcuts import render
from django.contrib.auth.decorators import login_required


import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Ticket, Department, TicketSubject

import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Ticket, Department, TicketSubject

@login_required
def ticket_list(request):
    user = request.user
    
    # 1. Chamados que o próprio usuário abriu (visível para todos)
    my_tickets = Ticket.objects.filter(requester=user).order_by('-created_at')
    
    # 2. NOVA REGRA: Apenas "administrador" ou "departamento pessoal" tratam chamados
    # Mapeamos os nomes exatos dos grupos cadastrados no seu painel administrativo do Django
    grupos_permitidos = [
        'administrador', 'Administrador', 
        'departamento pessoal', 'Departamento Pessoal', 'DP'
    ]
    
    # Verificamos se o usuário pertence a qualquer um dos grupos acima
    is_agent = user.groups.filter(name__in=grupos_permitidos).exists()
    
    incoming_tickets = []
    if is_agent:
        # Se for do grupo permitido, filtramos os chamados destinados ao departamento DELE
        if hasattr(user, 'department') and user.department:
            incoming_tickets = Ticket.objects.filter(department=user.department).order_by('-created_at')
        else:
            # Caso o usuário seja Administrador e não tenha departamento fixo no cadastro, 
            # ele poderá ver os chamados de todos os setores como fallback.
            incoming_tickets = Ticket.objects.all().order_by('-created_at')

    # Preparando dados para o Modal de Categorização de 4 níveis
    departments = Department.objects.all()
    all_subjects = TicketSubject.objects.all()
    subjects_data = [{
        'id': s.id,
        'name': s.name,
        'department_id': s.department_id,
        'parent_id': s.parent_id
    } for s in all_subjects]
        
    context = {
        'my_tickets': my_tickets,
        'incoming_tickets': incoming_tickets,
        'is_agent': is_agent,  # Diz ao HTML se exibe a aba de tratamento do setor
        'departments': departments,
        'subjects_json': json.dumps(subjects_data), 
    }
    return render(request, 'ticket_list.html', context)

@login_required
def ticket_create(request):
    return render(request, 'ticket_list.html')
