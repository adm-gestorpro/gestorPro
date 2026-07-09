from datetime import date, datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import F, Value, CharField, Count, Q, Case, When, ExpressionWrapper, DurationField
from django.db.models.functions import ExtractDay
from django.http import QueryDict
from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import JsonResponse

from produtos.models import Produto, Validade
from controle.models import Loja

from controle.scripts.consulta_estoques import consulta_estoque


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
    # Alimenta o array de busca instantânea do JavaScript (tanto no GET quanto no POST)
    produtos_modal = Produto.objects.all()

    query = ''
    produtos_resultado = []

    if request.method == 'POST':
        # Correção: Como o formulário no HTML usa method="POST", pegamos do request.POST
        query = request.POST.get('q', '').strip()

        # Só realiza a busca se o usuário tiver digitado ou escaneado algo
        if query:
            # 1. Filtra os produtos por Código Interno, EAN/GTIN ou Descrição (case-insensitive)
            produtos_queryset = Produto.objects.filter(
                Q(cod_produto__icontains=query) |
                Q(cod_gtin_principal__icontains=query) |
                Q(desc_produto__icontains=query)
            ).distinct()

            # 2. Identifica quais lojas o usuário logado tem permissão para acessar
            lojas_usuario = request.user.perfil.get_lojas_acessiveis()

            data_atual = timezone.now().date()

            # 3. Monta a estrutura de dados rica que o HTML precisa renderizar
            for produto in produtos_queryset:
                lojas_acesso_dados = []

                for loja in lojas_usuario:
                    # Mantida a sua estrutura original comentada/configurada
                    # relacao_estoque = EstoquePreco.objects.filter(
                    #     produto=produto, 
                    #     loja=loja
                    # ).first()
                    relacao_estoque = consulta_estoque(produto, loja)

                    # Se houver registro de estoque/preço para a loja, processa as validades
                    if relacao_estoque:
                        # Busca as validades/lotes deste produto nesta loja específica
                        validades_queryset = Validade.objects.filter(
                            id_produto=produto,
                            cod_loja=loja.cod_loja,
                            qt_lote__gt=0  # Apenas lotes que ainda possuem saldo
                        ).order_by('dt_validade')

                        lista_validades = []
                        for val in validades_queryset:
                            lista_validades.append({
                                'data_validade': val.dt_validade.strftime('%d/%m/%Y'),
                                'lote': val.num_lote,
                                'quantidade': val.qt_lote,
                                'vencido': val.dt_validade < data_atual  # Flag para colorir de vermelho se vencido
                            })

                        lojas_acesso_dados.append({
                            'id_loja': loja.cod_loja,
                            #'preco_venda': relacao_estoque.preco_venda,
                            'estoque_disponivel': relacao_estoque,
                            'validades': lista_validades
                        })

                # Adiciona os atributos dinâmicos ao objeto do produto para leitura direta no template
                produto.lojas_acesso = lojas_acesso_dados
                produtos_resultado.append(produto)
    
    # Contexto unificado retornando sempre os produtos do modal para o autocompletar funcionar
    context = {
        'query': query,
        'produtos': produtos_resultado,
        'produtos_modal': produtos_modal,
    }
    
    return render(request, 'listar_produtos.html', context)


@login_required
def cadastrar_lote(request):
    return render(request, 'controle_validade/validade_dashboard.html')


@login_required
@checa_multiplos_grupos_403(['Administrador', 'Diretoria', 'Gerente de Loja', 'Gerente Distrital', 'Atendente/Vendedor'])
def api_buscar_produtos(request):
    termo = request.GET.get('q', '').strip()
    
    # Só busca no banco se o usuário tiver digitado pelo menos 2 caracteres
    if len(termo) < 2:
        return JsonResponse({'resultados': []})
        
    produtos = Produto.objects.filter(
        caixa=False
    ).filter(
        Q(desc_produto__icontains=termo) |
        Q(cod_produto__icontains=termo) |
        Q(cod_gtin_principal__icontains=termo)
    ).only('cod_produto', 'desc_produto', 'cod_gtin_principal')

    resultados = [
        {
            'id': p.cod_produto,
            'nome': p.desc_produto,
            'codigo_interno': p.cod_produto,
            'codigo_barras': p.cod_gtin_principal or ''
        }
        for p in produtos
    ]
    
    return JsonResponse({'resultados': resultados})

@login_required
@checa_multiplos_grupos_403(['Administrador', 'Diretoria', 'Gerente de Loja', 'Gerente Distrital', 'Atendente/Vendedor'])
def controle_validade(request):
    perfil = request.user.perfil
    lojas_permitidas = perfil.get_lojas_acessiveis()

    # 1. Parâmetros da requisição
    filtro_status = request.GET.get('status', '').strip().lower()
    filtro_loja = request.GET.get('loja', '').strip()
    query = request.GET.get('q', '').strip()
    per_page = request.GET.get('per_page', '50')
    if per_page not in ['50', '100', '200']: 
        per_page = '50'

    hoje = date.today()

    # 2. QuerySet Base Otimizado (select_related essencial)
    validades_qs = Validade.objects.filter(
        ativo=True, 
        cod_loja__in=lojas_permitidas
    ).select_related('id_produto', 'cod_loja', 'usuario_cadastro')

    if filtro_loja:
        validades_qs = validades_qs.filter(cod_loja__cod_loja=filtro_loja)

    # 3. Preparação de datas fixas para os Ranges
    trinta_dias = hoje + timedelta(days=30)
    sessenta_dias = hoje + timedelta(days=60)
    noventa_dias = hoje + timedelta(days=90)

    # 4. Métricas calculadas em query dedicada (Garante cache do banco)
    metricas = validades_qs.aggregate(
        total_vencidos=Count('id', filter=Q(dt_validade__lt=hoje)),
        total_critico=Count('id', filter=Q(dt_validade__gte=hoje, dt_validade__lte=trinta_dias)),
        total_atencao=Count('id', filter=Q(dt_validade__gt=trinta_dias, dt_validade__lte=sessenta_dias)),
        total_observacao=Count('id', filter=Q(dt_validade__gt=sessenta_dias, dt_validade__lte=noventa_dias)),
        total_seguro=Count('id', filter=Q(dt_validade__gt=noventa_dias))
    )

    # 5. Aplicação de filtros textuais se existirem
    if query:
        validades_qs = validades_qs.filter(
            Q(id_produto__desc_produto__icontains=query) |
            Q(id_produto__cod_produto__icontains=query) |
            Q(id_produto__cod_gtin_principal__icontains=query) |
            Q(num_lote__icontains=query)
        )

    # 6. Filtros de Status baseados nas datas calculadas
    if filtro_status == 'vencido':
        validades_qs = validades_qs.filter(dt_validade__lt=hoje)
    elif filtro_status == 'critico':
        validades_qs = validades_qs.filter(dt_validade__gte=hoje, dt_validade__lte=trinta_dias)
    elif filtro_status == 'atencao':
        validades_qs = validades_qs.filter(dt_validade__gt=trinta_dias, dt_validade__lte=sessenta_dias)
    elif filtro_status == 'observacao':
        validades_qs = validades_qs.filter(dt_validade__gt=sessenta_dias, dt_validade__lte=noventa_dias)
    elif filtro_status == 'seguro':
        validades_qs = validades_qs.filter(dt_validade__gt=noventa_dias)

    # 7. Ordenação nativa e Paginação eficiente
    validades_qs = validades_qs.order_by('dt_validade')
    paginator = Paginator(validades_qs, int(per_page))
    page_obj = paginator.get_page(request.GET.get('page'))

    # 8. Anotação Dinâmica no Python de atributos voláteis (Rápido e mantém o Objeto ativo)
    for p in page_obj.object_list:
        dias_restantes = (p.dt_validade - hoje).days
        p.dias_restantes = dias_restantes  # Injeta direto no objeto na memória
        
        if dias_restantes < 0:
            p.status_texto = "Vencido"
            p.badge_class = "bg-rose-100 text-rose-800 border-rose-200"
            p.badge_dot = "bg-rose-500"
        elif dias_restantes <= 30:
            p.status_texto = "Crítico"
            p.badge_class = "bg-red-100 text-red-800 border-red-200"
            p.badge_dot = "bg-red-500"
        elif dias_restantes <= 60:
            p.status_texto = "Atenção"
            p.badge_class = "bg-orange-100 text-orange-800 border-orange-200"
            p.badge_dot = "bg-orange-500"
        elif dias_restantes <= 90:
            p.status_texto = "Observação"
            p.badge_class = "bg-yellow-100 text-yellow-800 border-yellow-200"
            p.badge_dot = "bg-yellow-500"
        else:
            p.status_texto = "Seguro"
            p.badge_class = "bg-emerald-100 text-emerald-800 border-emerald-200"
            p.badge_dot = "bg-emerald-500"

        # Captura amigável do primeiro nome do usuário cadastrado
        p.lancado_por_nome = p.usuario_cadastro.first_name if p.usuario_cadastro else 'Sistema'

    # 9. Consultas auxiliares leves
    lojas = Loja.objects.filter(cod_loja__in=lojas_permitidas).order_by('cod_loja')

    context = {
        'page_obj': page_obj,
        'filtro_status': filtro_status,
        'filtro_loja': filtro_loja,
        'query': query,
        'per_page': int(per_page),
        'contagem_vencidos': metricas['total_vencidos'] or 0,
        'contagem_30': metricas['total_critico'] or 0,
        'contagem_60': metricas['total_atencao'] or 0,
        'contagem_90': metricas['total_observacao'] or 0,
        'contagem_seguro': metricas['total_seguro'] or 0,
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
        ).exists()

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
            # OTIMIZAÇÃO EXTREMA: Soma direto no banco usando F expressions (Não puxa dados pra memória)
            Validade.objects.filter(
                id_produto=consulta_produto,
                num_lote__iexact=dados['lote'].strip(),
                cod_loja=consulta_loja
            ).update(
                qt_lote=F('qt_lote') + float(dados['quantidade']),
                usuario_ultimo=request.user
            )
            
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
        # CORREÇÃO: Como o JS usa Fetch, retornamos JSON para responder em 10ms
        return JsonResponse({'status': 'success'})
        
    return JsonResponse({'status': 'error', 'message': 'Método inválido'}, status=400)


@login_required
@checa_multiplos_grupos_403(['Administrador', 'Diretoria', 'Gerente de Loja', 'Gerente Distrital'])
def inativar_validade(request, id):
    if request.method == 'POST':
        Validade.objects.filter(id=id).update(ativo=False, usuario_ultimo=request.user)
        # CORREÇÃO: Resposta instantânea sem carregar a view pesada por trás
        return JsonResponse({'status': 'success'})
        
    return JsonResponse({'status': 'error', 'message': 'Método inválido'}, status=400)