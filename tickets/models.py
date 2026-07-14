from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Department(models.Model):
    """
    Representa os setores da empresa (ex: TI, RH, Financeiro).
    Cada setor possui sua própria fila de atendimento.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nome do Setor")
    description = models.TextField(blank=True, null=True, verbose_name="Descrição")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"
        ordering = ['name']

    def __str__(self):
        return self.name


class SLAPolicy(models.Model):
    """
    Define as metas de tempo de atendimento baseadas no Setor e na Prioridade.
    """
    PRIORITY_CHOICES = [
        ('LOW', 'Baixa'),
        ('MEDIUM', 'Média'),
        ('HIGH', 'Alta'),
        ('CRITICAL', 'Crítica'),
    ]

    department = models.ForeignKey(
        Department, 
        on_delete=models.CASCADE, 
        related_name='sla_policies',
        verbose_name="Setor"
    )
    priority = models.CharField(
        max_length=10, 
        choices=PRIORITY_CHOICES, 
        verbose_name="Prioridade"
    )
    response_time_minutes = models.PositiveIntegerField(
        verbose_name="Tempo de Resposta (minutos)",
        help_text="Tempo máximo para o primeiro contato técnico iniciar."
    )
    resolution_time_hours = models.PositiveIntegerField(
        verbose_name="Tempo de Resolução (horas)",
        help_text="Tempo total para resolver e encerrar a demanda."
    )

    class Meta:
        verbose_name = "Política de SLA"
        verbose_name_plural = "Políticas de SLA"
        # Garante que não existam duas políticas idênticas para o mesmo setor e prioridade
        unique_together = ('department', 'priority')

    def __str__(self):
        return f"{self.department.name} - {self.get_priority_display()}"


class Ticket(models.Model):
    """
    Armazena o registro principal do chamado/ticket.
    """
    STATUS_CHOICES = [
        ('OPEN', 'Aberto'),
        ('IN_PROGRESS', 'Em Atendimento'),
        ('PAUSED', 'Pausado'),
        ('RESOLVED', 'Resolvido'),
        ('CLOSED', 'Fechado'),
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'Baixa'),
        ('MEDIUM', 'Média'),
        ('HIGH', 'Alta'),
        ('CRITICAL', 'Crítica'),
    ]

    title = models.CharField(max_length=200, verbose_name="Título/Assunto")
    description = models.TextField(verbose_name="Descrição da Demanda")
    
    # Relacionamentos com o Usuário Customizado do Django
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='requested_tickets',
        verbose_name="Solicitante"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name="Atendente Responsável"
    )
    
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name="Setor Destino"
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='OPEN', 
        verbose_name="Status"
    )
    priority = models.CharField(
        max_length=10, 
        choices=PRIORITY_CHOICES, 
        verbose_name="Prioridade"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Fechado em")
    
    # Prazos Calculados de SLA (Armazenados fisicamente no banco para performance)
    sla_response_deadline = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Limite de Primeiro Atendimento"
    )
    sla_resolution_deadline = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Limite de Resolução"
    )
    
    # Flags de estouro do SLA
    sla_response_breached = models.BooleanField(
        default=False, 
        verbose_name="Estourou SLA de Resposta"
    )
    sla_resolution_breached = models.BooleanField(
        default=False, 
        verbose_name="Estourou SLA de Resolução"
    )

    class Meta:
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"
        ordering = ['-created_at']
        # Índices aceleram consultas de listagem e filtragem no GestorPro
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['department']),
            models.Index(fields=['requester']),
        ]

    def save(self, *args, **kwargs):
        # Detecta se é a criação do Ticket
        is_new = self.pk is None
        
        if is_new:
            # Tenta buscar as metas de SLA configuradas para o par Setor/Prioridade
            try:
                policy = SLAPolicy.objects.get(department=self.department, priority=self.priority)
                
                # CÁLCULO DE SLA: Tempo linear (24/7) padrão.
                # Se precisar descontar finais de semana/horário comercial,
                # recomenda-se isolar esse cálculo em um helper utilizando o pacote python 'workalendar'
                self.sla_response_deadline = timezone.now() + timedelta(minutes=policy.response_time_minutes)
                self.sla_resolution_deadline = timezone.now() + timedelta(hours=policy.resolution_time_hours)
                
            except SLAPolicy.DoesNotExist:
                # Caso o setor não tenha uma política de SLA cadastrada, assume-se prazos nulos
                self.sla_response_deadline = None
                self.sla_resolution_deadline = None

        # Gerencia data de encerramento automaticamente
        if self.status in ['RESOLVED', 'CLOSED'] and not self.closed_at:
            self.closed_at = timezone.now()
            # Verifica se o fechamento violou a data limite definida no SLA de Resolução
            if self.sla_resolution_deadline and self.closed_at > self.sla_resolution_deadline:
                self.sla_resolution_breached = True
        elif self.status not in ['RESOLVED', 'CLOSED']:
            self.closed_at = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.id} | {self.title[:30]}... ({self.get_status_display()})"


class TicketComment(models.Model):
    """
    Interações/Histórico dentro do Ticket.
    Funciona tanto para mensagens públicas (solicitante <> atendente) 
    quanto notas internas privadas de controle de equipe.
    """
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Ticket"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Autor"
    )
    message = models.TextField(verbose_name="Mensagem")
    
    is_internal = models.BooleanField(
        default=False,
        verbose_name="Nota Interna",
        help_text="Se marcado, apenas os atendentes do setor conseguem visualizar essa mensagem."
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Enviado em")

    class Meta:
        verbose_name = "Interação do Ticket"
        verbose_name_plural = "Interações do Ticket"
        ordering = ['created_at']

    def __str__(self):
        tipo = "Interno" if self.is_internal else "Público"
        return f"Comentário por {self.author.get_full_name() or self.author.username} ({tipo})"


class TicketSubject(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='subjects')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')

    def get_full_path(self):
        """Retorna o caminho completo da árvore (ex: Hardware > Impressoras > Toner)"""
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return " ➔ ".join(path)

    def __str__(self):
        return self.get_full_path()