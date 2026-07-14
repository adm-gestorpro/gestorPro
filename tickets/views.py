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

import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Ticket, Department, TicketSubject

@login_required
def ticket_list(request):
    user = request.user
    
    # 1. MINHAS SOLICITAÇÕES: Chamados abertos pelo usuário (Todos veem)
    my_tickets = Ticket.objects.filter(requester=user).order_by('-created_at')
    
    # 2. CONTROLE DE ACESSO (RBAC) E FILAS DE ATENDIMENTO
    # Usamos '__icontains' para abranger variações de digitação (ex: Administrador, administradores)
    is_admin = user.groups.filter(name__icontains='administrador').exists()
    
    # Liste aqui os nomes EXATOS dos grupos que resolvem chamados no seu sistema
    grupos_departamentais = [
        'Departamento Pessoal', 'Suporte', 'Financeiro', 'Contábil', 'TI', 'Manutenção'
    ]
    is_agent_dept = user.groups.filter(name__in=grupos_departamentais).exists()
    
    # A aba de "Fila de Atendimento" só aparece se ele for Admin ou de um dos grupos acima
    is_agent = is_admin or is_agent_dept
    
    incoming_tickets = []
    if is_agent:
        if is_admin:
            # Regra de Ouro do Admin: Visão global, ignora filtros de setor
            incoming_tickets = Ticket.objects.all().order_by('-created_at')
            
        elif is_agent_dept:
            # Regra Departamental: Vê APENAS chamados roteados para o departamento do perfil dele
            if hasattr(user, 'department') and user.department:
                incoming_tickets = Ticket.objects.filter(department=user.department).order_by('-created_at')
            else:
                # Fallback de Segurança: Se o usuário estiver no grupo 'Financeiro' mas o 
                # cadastro dele estiver sem um 'department' preenchido, ele não verá nada 
                # para evitar vazamento de dados de outras áreas.
                incoming_tickets = Ticket.objects.none()

    # 3. PREPARAÇÃO DO MODAL DE NOVA DEMANDA (CASCATA)
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
        'is_agent': is_agent, # Flag booleana que liga/desliga a Aba 2 no HTML
        'departments': departments,
        'subjects_json': json.dumps(subjects_data), 
    }
    return render(request, 'ticket_list.html', context)

@login_required
def ticket_create(request):
    return render(request, 'ticket_list.html')
