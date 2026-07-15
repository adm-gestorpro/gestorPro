from django.shortcuts import render, redirect
from django.contrib import messages
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
        'is_agent': is_agent, 
        'departments': departments,
        'subjects_json': subjects_data, # <--- ENVIE A LISTA PURA DO PYTHON
    }
    return render(request, 'ticket_list.html', context)

@login_required
def ticket_create(request):
    if request.method == 'POST':
        # 1. Captura os dados enviados pelo formulário HTML
        title = request.POST.get('title')
        department_id = request.POST.get('department')
        subject_id = request.POST.get('subject_id') # Este é o ID oculto gerado pela nossa cascata
        description = request.POST.get('description')

        # 2. Validação de Segurança Básica
        if not title or not department_id or not subject_id or not description:
            messages.error(request, "Por favor, preencha todos os campos obrigatórios da árvore de assunto.")
            return redirect('ticket_list')

        try:
            # Busca as instâncias do banco de dados
            department = Department.objects.get(id=department_id)
            subject = TicketSubject.objects.get(id=subject_id)

            # 3. Cria o chamado no banco de dados
            Ticket.objects.create(
                title=title,
                description=description,
                department=department,
                subject_id=subject.id,
                requester=request.user,  # Quem abriu o chamado
                status='OPEN',           # Status inicial padrão
                priority='NOT_SET'       # Como removemos a urgência do usuário, definimos um padrão
            )
            
            # Mensagem de sucesso (aparecerá naquele banner superior do seu base.html)
            messages.success(request, "Chamado aberto e encaminhado com sucesso!")
            
        except Department.DoesNotExist:
            messages.error(request, "O setor selecionado é inválido.")
        except TicketSubject.DoesNotExist:
            messages.error(request, "O assunto selecionado é inválido.")
        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao processar sua solicitação: {str(e)}")

    # Independente de dar certo ou errado, devolve o usuário para a tela de chamados
    return redirect('ticket_list')
