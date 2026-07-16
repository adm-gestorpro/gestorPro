from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Ticket, Department, TicketSubject, TicketComment

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
    subjects_data = []
    for s in TicketSubject.objects.prefetch_related('department').all():
        subjects_data.append({
            'id': s.id,
            'name': s.name,
            'parent_id': s.parent_id if s.parent_id else None,
            # Aqui está a chave: uma lista de IDs de departamentos associados
            'department_ids': list(s.department.values_list('id', flat=True))
        })
        
    context = {
        'subjects_json': subjects_data,
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


@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    user = request.user

    # 1. VALIDAÇÃO DE PERMISSÃO
    is_requester = (ticket.requester == user)
    is_admin = user.groups.filter(name__icontains='administrador').exists()
    grupos_departamentais = ['Departamento Pessoal', 'Suporte', 'Financeiro', 'Contábil', 'TI', 'Manutenção']
    is_agent_dept = user.groups.filter(name__in=grupos_departamentais).exists()
    
    is_agent = is_admin or is_agent_dept

    if not (is_requester or is_agent):
        messages.error(request, "Você não tem permissão para visualizar este chamado.")
        return redirect('ticket_list')

    # 2. PROCESSAMENTO DE AÇÕES (POST)
    if request.method == 'POST':
        action = request.POST.get('action')

        # --- BLOQUEIO DE SEGURANÇA: Ações exclusivas para Agentes ---
        # Lista de ações que SOMENTE agentes podem realizar
        acoes_agente = [
            'add_internal_note', 'edit_internal_note', 'delete_internal_note', 
            'take_ticket', 'update_ticket'
        ]
        
        if action in acoes_agente and not is_agent:
            messages.error(request, "Você não tem permissão para realizar esta ação de gestão.")
            return redirect('ticket_detail', ticket_id=ticket.id)

        # Se o chamado estiver fechado, ninguém (exceto admins para reabrir) pode falar
        if ticket.status == 'CLOSED' and action == 'add_comment':
            messages.warning(request, "Chamado finalizado, não é possível responder.")
            return redirect('ticket_detail', ticket_id=ticket.id)

        # --- PROCESSAMENTO SEGURO ---
        if action == 'add_comment':
            text = request.POST.get('text')
            if text:
                TicketComment.objects.create(ticket=ticket, author=user, text=text, is_internal=False)
                # Opcional: Se for agente respondendo, pode alterar status automaticamente
                if is_agent and ticket.status == 'OPEN':
                    ticket.status = 'IN_PROGRESS'
                    ticket.save()
                messages.success(request, "Mensagem enviada.")

        elif action == 'add_internal_note' and is_agent:
            text = request.POST.get('text')
            if text:
                TicketComment.objects.create(ticket=ticket, author=user, text=text, is_internal=True)
                messages.success(request, "Nota interna salva.")

        elif action == 'edit_internal_note' and is_agent:
            note_id = request.POST.get('note_id')
            new_text = request.POST.get('text')
            note = get_object_or_404(TicketComment, id=note_id, ticket=ticket, is_internal=True)
            note.text = new_text
            note.save()

        elif action == 'delete_internal_note' and is_agent:
            note_id = request.POST.get('note_id')
            note = get_object_or_404(TicketComment, id=note_id, ticket=ticket, is_internal=True)
            note.delete()

        elif action == 'take_ticket' and is_agent:
            ticket.assignee = user
            ticket.status = 'IN_PROGRESS'
            ticket.save()

        elif action == 'update_ticket' and is_agent:
            # Lógica de atualização de status/prioridade...
            new_status = request.POST.get('status')
            new_priority = request.POST.get('priority')
            if new_status: ticket.status = new_status
            if new_priority: ticket.priority = new_priority
            ticket.save()

        return redirect('ticket_detail', ticket_id=ticket.id)

    # 3. SEPARAÇÃO E ORDENAÇÃO DE MENSAGENS
    # order_by('-created_at') traz da MAIS RECENTE para a MAIS ANTIGA
    public_comments = ticket.comments.filter(is_internal=False).order_by('-created_at')
    
    # Solicitantes NUNCA carregam as notas internas no banco
    internal_notes = ticket.comments.filter(is_internal=True).order_by('-created_at') if is_agent else []

    context = {
        'ticket': ticket,
        'public_comments': public_comments,
        'internal_notes': internal_notes,
        'is_agent': is_agent,
        'is_requester': is_requester
    }
    return render(request, 'ticket_detail.html', context)