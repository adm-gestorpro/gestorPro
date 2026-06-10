from datetime import date, datetime
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import F, Value, CharField, Count, Q, Case, When, ExpressionWrapper, DurationField
from django.db.models.functions import ExtractDay
from django.http import QueryDict
from django.shortcuts import render, redirect

from produtos.models import Produto, Validade
from controle.models import Loja


@login_required
def erro_403_customizado(request, exception=None):
    contexto = {
        'usuario': request.user,
        'mensagem_extra': "Área restrita para a gerência."
    }
    return render(request, '403.html', contexto, status=403)


def checa_multiplos_grupos_403(nomes_grupos):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.user.groups.filter(name__in=nomes_grupos).exists():
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return _wrapped_view
    return decorator


@login_required
def listar_produtos(request):
    produtos_list = Produto.objects.all().order_by('cod_produto')

    per_page = request.GET.get('per_page', 10)
    paginator = Paginator(produtos_list, per_page)

    page_number = request.GET.get('page')
    produtos = paginator.get_page(page_number)

    context = {'produtos': produtos, 'per_page': int(per_page)}
    return render(request, 'listar_produtos.html', context)


@login_required
def cadastrar_lote(request):
    return render(request, 'controle_validade/validade_dashboard.html')


@login_required
@checa_multiplos_grupos_403(['Administrador', 'Diretoria', 'Gerente de Loja', 'Gerente Distrital', 'Atendente/Vendedor'])
def controle_validade(request):
    perfil = request.user.perfil
    lojas_permitidas = perfil.get_lojas_acessiveis()

    # 1. Parâmetros da requisição
    filtro_status = request.GET.get('status', '').strip().lower()
    query = request.GET.get('q', '').strip()
    per_page = request.GET.get('per_page', '10')
    if per_page not in ['10', '20', '50']: 
        per_page = '10'

    hoje = date.today()

    # 2. QuerySet Base (Otimizado com select_related)
    validades_qs = Validade.objects.filter(
        ativo=True, 
        cod_loja__in=lojas_permitidas
    ).select_related('id_produto', 'cod_loja')

    # 3. Processamento de Datas e Estilos direto no PostgreSQL (Supabase)
    validades_qs = validades_qs.annotate(
        dias_restantes=ExtractDay(
            ExpressionWrapper(F('dt_validade') - Value(hoje), output_field=DurationField())
        )
    ).annotate(
        status_texto=Case(
            When(dias_restantes__lt=0, then=Value("Vencido")),
            When(dias_restantes__gte=0, dias_restantes__lte=30, then=Value("Crítico")),
            When(dias_restantes__gt=30, dias_restantes__lte=60, then=Value("Atenção")),
            When(dias_restantes__gt=60, dias_restantes__lte=90, then=Value("Observação")),
            default=Value("Seguro"),
            output_field=CharField()
        ),
        badge_class=Case(
            When(dias_restantes__lt=0, then=Value("bg-black-100 text-white-900 border-black-300")),
            When(dias_restantes__gte=0, dias_restantes__lte=30, then=Value("bg-red-100 text-red-800 border-red-200")),
            When(dias_restantes__gt=30, dias_restantes__lte=60, then=Value("bg-orange-100 text-orange-800 border-orange-200")),
            When(dias_restantes__gt=60, dias_restantes__lte=90, then=Value("bg-yellow-100 text-yellow-800 border-yellow-200")),
            default=Value("bg-emerald-100 text-emerald-800 border-emerald-200"),
            output_field=CharField()
        )
    )

    # 4. Métricas calculadas em uma única query agregada de alta velocidade
    metricas = validades_qs.aggregate(
        total_vencidos=Count('id', filter=Q(dias_restantes__lt=0)),
        total_critico=Count('id', filter=Q(dias_restantes__gte=0, dias_restantes__lte=30)),
        total_atencao=Count('id', filter=Q(dias_restantes__gt=30, dias_restantes__lte=60)),
        total_observacao=Count('id', filter=Q(dias_restantes__gt=60, dias_restantes__lte=90)),
        total_seguro=Count('id', filter=Q(dias_restantes__gt=90))
    )

    # 5. Filtros textuais aplicados na busca do Banco
    if query:
        validades_qs = validades_qs.filter(
            Q(id_produto__desc_produto__icontains=query) |
            Q(id_produto__cod_produto__icontains=query) |
            Q(id_produto__cod_gtin_principal__icontains=query) |
            Q(num_lote__icontains=query)
        )

    # 6. Filtros de Status aplicados na busca do Banco
    if filtro_status == 'vencido':
        validades_qs = validades_qs.filter(dias_restantes__lt=0)
    elif filtro_status == 'critico':
        validades_qs = validades_qs.filter(dias_restantes__gte=0, dias_restantes__lte=30)
    elif filtro_status == 'atencao':
        validades_qs = validades_qs.filter(dias_restantes__gt=30, dias_restantes__lte=60)
    elif filtro_status == 'observacao':
        validades_qs = validades_qs.filter(dias_restantes__gt=60, dias_restantes__lte=90)
    elif filtro_status == 'seguro':
        validades_qs = validades_qs.filter(dias_restantes__gt=90)

    # 7. Ordenação nativa por data de vencimento
    validades_qs = validades_qs.order_by('dt_validade')

    # 8. Paginação eficiente (Trafega apenas o limite configurado por página)
    paginator = Paginator(validades_qs, int(per_page))
    page_obj = paginator.get_page(request.GET.get('page'))

    # Mapeamento do subset da página atual para dicionários (Mantém compatibilidade com o Template Frontend)
    lista_paginada_dict = []
    for p in page_obj.object_list:
        lista_paginada_dict.append({
            'id': p.id,
            'nome': p.id_produto.desc_produto,
            'loja': p.cod_loja.cod_loja,
            'codigo_interno': p.id_produto.cod_produto,
            'codigo_barras': p.id_produto.cod_gtin_principal,
            'lote': p.num_lote,
            'qt_lote': p.qt_lote,
            'tipo_lote': p.tipo_lote,
            'dt_validade': p.dt_validade,
            'obs_geral': p.obs_geral,
            'ativo': p.ativo,
            'lancado_por': p.usuario_cadastro.first_name if p.usuario_cadastro else '',
            'data_cadastro': p.data_cadastro,
            'promocao_ativa': p.promocao_ativa,
            'dias_restantes': p.dias_restantes,
            'badge_class': p.badge_class,
            'status_texto': p.status_texto
        })
    
    # Injeta a lista convertida de volta ao objeto de paginação
    page_obj.object_list = lista_paginada_dict

    # 9. Consultas auxiliares otimizadas para o Modal
    produtos_query = Produto.objects.filter(caixa=False).only('cod_produto', 'desc_produto', 'cod_gtin_principal')
    lojas = Loja.objects.filter(cod_loja__in=lojas_permitidas)

    context = {
        'page_obj': page_obj,
        'filtro_status': filtro_status,
        'query': query,
        'per_page': int(per_page),
        'contagem_vencidos': metricas['total_vencidos'] or 0,
        'contagem_30': metricas['total_critico'] or 0,
        'contagem_60': metricas['total_atencao'] or 0,
        'contagem_90': metricas['total_observacao'] or 0,
        'contagem_seguro': metricas['total_seguro'] or 0,
        'produtos_modal': produtos_query,
        'lojas': lojas,
    }
    
    return render(request, 'controle_validade/validade_dashboard.html', context)


@login_required
@checa_multiplos_grupos_403(['Administrador', 'Diretoria', 'Gerente de Loja', 'Gerente Distrital', 'Atendente/Vendedor'])
def cadastrar_validade(request):
    if request.method == 'POST':
        dados = request.POST.dict()
        consulta_produto = Produto.objects.get(cod_produto=dados['produto'])
        consulta_loja = Loja.objects.get(cod_loja=dados['loja'])
        consulta_validade = Validade.objects.filter(
            id_produto=consulta_produto, 
            num_lote__iexact=dados['lote'].strip(), 
            cod_loja=consulta_loja
        ).exists()  # .exists() é mais rápido do que trazer o objeto inteiro

        if not consulta_validade:
            validade = Validade(
                id_produto=consulta_produto,
                cod_loja=consulta_loja,
                num_lote=dados['lote'].upper().strip(),
                dt_validade=datetime.strptime(dados['data_validade'], "%Y-%m-%d"),
                qt_lote=dados['quantidade'],
                tipo_lote=dados.get('troca_fornecedor'),
                obs_geral=dados.get('observacoes', ''),
                usuario_cadastro=request.user,
                usuario_ultimo=request.user,
            )
            validade.save()
        else:
            qt_lote = float(Validade.objects.filter(id_produto=consulta_produto,num_lote__iexact=dados['lote'].strip(),cod_loja=consulta_loja).values('qt_lote')[0]['qt_lote']) + float(dados['quantidade'])
            Validade.objects.filter(id_produto=consulta_produto,num_lote__iexact=dados['lote'].strip(),cod_loja=consulta_loja).update(qt_lote=qt_lote)
    return redirect('controle_validade')


@login_required
@checa_multiplos_grupos_403(['Administrador', 'Diretoria', 'Gerente de Loja', 'Gerente Distrital'])
def editar_validade(request, id):
    if request.method == 'PUT':
        put_data = QueryDict(request.body)
        dados = put_data.dict()
                
        Validade.objects.filter(id=id).update(
            num_lote=dados['lote'].upper().strip(),
            dt_validade=datetime.strptime(dados['data_validade'], "%Y-%m-%d"),
            qt_lote=dados['quantidade'],
            tipo_lote=dados.get('troca_fornecedor'),
            obs_geral=dados.get('observacoes', ''),
            usuario_ultimo=request.user,
            promocao_ativa=dados.get('promocao_ativa', False)
        )
    return redirect('controle_validade')


@login_required
@checa_multiplos_grupos_403(['Administrador', 'Diretoria', 'Gerente de Loja', 'Gerente Distrital'])
def inativar_validade(request, id):
    if request.method == 'DELETE':
        Validade.objects.filter(id=id).update(ativo=False, usuario_ultimo=request.user)
    return redirect('controle_validade')