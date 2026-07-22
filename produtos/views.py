from datetime import date, datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import F, Value, CharField, Count, Q, Case, When, ExpressionWrapper, DurationField
from django.db.models.functions import ExtractDay
from django.http import QueryDict
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse

from produtos.models import Produto, Validade, Ruptura
from controle.models import Loja, Rede

from controle.scripts.consulta_estoques import consulta_estoque
from controle.scripts.consulta_precos import consulta_preco


# ==========================================
# FUNÇÃO AUXILIAR DE PERMISSÃO DE RUPTURA
# ==========================================
def usuario_e_gestor_ou_comprador(user):
    """Retorna True apenas se o usuário for superuser ou pertencer aos grupos de gestão/compras."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    
    grupos_gestao = ['Administrador', 'Diretoria', 'Comprador', 'Gestor']
    if user.groups.filter(name__in=grupos_gestao).exists():
        return True
        
    # Checagem segura caso haja propriedade no Perfil (executa se for chamável)
    if hasattr(user, 'perfil'):
        val = getattr(user.perfil, 'e_gestor_ou_comprador', False)
        if callable(val):
            return bool(val())
        return bool(val)
        
    return False


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
def buscar_produtos_api(request):
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'produtos': []})

    produtos = Produto.objects.filter(
        Q(cod_produto__icontains=query) |
        Q(cod_gtin_principal__icontains=query) |
        Q(desc_produto__icontains=query)
    ).distinct()[:15]

    resultados = []
    for p in produtos:
        resultados.append({
            'id': p.cod_produto,
            'nome': p.desc_produto,
            'codigo_interno': p.cod_produto,
            'codigo_barras': p.cod_gtin_principal if p.cod_gtin_principal else ''
        })

    return JsonResponse({'produtos': resultados})

@login_required
def listar_produtos(request):
    query = ''
    produtos_resultado = []

    if request.method == 'POST':
        produto_id = request.POST.get('produto_id', '').strip()
        query = request.POST.get('q', '').strip()

        produtos_queryset = []

        if produto_id:
            produtos_queryset = Produto.objects.filter(cod_gtin_principal=produto_id)
        elif query:
            produtos_queryset = Produto.objects.filter(
                Q(cod_gtin_principal=query)
            )

        if produtos_queryset:
            lojas_usuario = request.user.perfil.get_lojas_acessiveis()

            if hasattr(lojas_usuario, 'values_list'):
                _ids_brutos = lojas_usuario.values_list('id_rede', flat=True).distinct()
                redes_ids = sorted({r for r in _ids_brutos if r})
            else:
                redes_ids = sorted({loja.rede_id for loja in lojas_usuario if getattr(loja, 'id_rede', None)})

            if redes_ids and lojas_usuario:
                lojas_para_consultar = Loja.objects.filter(
                    id_rede__in=redes_ids
                ).distinct().order_by('cod_loja')
            else:
                lojas_para_consultar = lojas_usuario

            data_atual = timezone.now().date()

            for produto in produtos_queryset:
                lojas_acesso_dados = []

                for loja in lojas_para_consultar:
                    relacao_estoque = consulta_estoque(produto, loja)
                    relacao_preco = consulta_preco(produto, loja)

                    if relacao_estoque:
                        validades_queryset = Validade.objects.filter(
                            id_produto=produto,
                            cod_loja=loja.cod_loja,
                            qt_lote__gt=0
                        ).order_by('dt_validade')

                        lista_validades = []
                        total_validades = 0.0

                        for val in validades_queryset:
                            lista_validades.append({
                                'data_validade': val.dt_validade.strftime('%d/%m/%Y'),
                                'lote': val.num_lote,
                                'quantidade': val.qt_lote,
                                'vencido': val.dt_validade < data_atual
                            })
                            total_validades += float(val.qt_lote)

                        try:
                            if hasattr(relacao_estoque, 'estoque_disponivel'):
                                qtd_estoque_loja = float(relacao_estoque.estoque_disponivel)
                            elif isinstance(relacao_estoque, dict):
                                qtd_estoque_loja = float(relacao_estoque.get('estoque_disponivel', 0))
                            else:
                                qtd_estoque_loja = float(relacao_estoque)
                        except (ValueError, TypeError, AttributeError):
                            qtd_estoque_loja = 0.0

                        estoque_desatualizado = round(total_validades, 3) != round(qtd_estoque_loja, 3)

                        lojas_acesso_dados.append({
                            'id_loja': loja.cod_loja,
                            'estoque_disponivel': relacao_estoque,
                            'validades': lista_validades,
                            'estoque_desatualizado': estoque_desatualizado,
                            'preco_venda': relacao_preco
                        })

                produto.lojas_acesso = lojas_acesso_dados
                produtos_resultado.append(produto)
    
    context = {
        'query': query,
        'produtos': produtos_resultado,
    }
    
    return render(request, 'listar_produtos.html', context)

@login_required
def cadastrar_lote(request):
    return render(request, 'controle_validade/validade_dashboard.html')

@login_required
@checa_multiplos_grupos_403(['Administrador', 'Diretoria', 'Gerente de Loja', 'Gerente Distrital', 'Atendente/Vendedor'])
def api_buscar_produtos(request):
    termo = request.GET.get('q', '').strip()
    
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

    filtro_status = request.GET.get('status', '').strip().lower()
    filtro_loja = request.GET.get('loja', '').strip()
    query = request.GET.get('q', '').strip()
    per_page = request.GET.get('per_page', '50')
    if per_page not in ['50', '100', '200', '500', '1000']: 
        per_page = '50'

    hoje = date.today()

    validades_qs = Validade.objects.filter(
        ativo=True, 
        cod_loja__in=lojas_permitidas
    ).select_related('id_produto', 'cod_loja', 'usuario_cadastro')

    if filtro_loja:
        validades_qs = validades_qs.filter(cod_loja__cod_loja=filtro_loja)

    trinta_dias = hoje + timedelta(days=30)
    sessenta_dias = hoje + timedelta(days=60)
    noventa_dias = hoje + timedelta(days=90)

    metricas = validades_qs.aggregate(
        total_vencidos=Count('id', filter=Q(dt_validade__lt=hoje)),
        total_critico=Count('id', filter=Q(dt_validade__gte=hoje, dt_validade__lte=trinta_dias)),
        total_atencao=Count('id', filter=Q(dt_validade__gt=trinta_dias, dt_validade__lte=sessenta_dias)),
        total_observacao=Count('id', filter=Q(dt_validade__gt=sessenta_dias, dt_validade__lte=noventa_dias)),
        total_seguro=Count('id', filter=Q(dt_validade__gt=noventa_dias))
    )

    if query:
        validades_qs = validades_qs.filter(
            Q(id_produto__desc_produto__icontains=query) |
            Q(id_produto__cod_produto__icontains=query) |
            Q(id_produto__cod_gtin_principal__icontains=query) |
            Q(num_lote__icontains=query)
        )

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

    validades_qs = validades_qs.order_by('dt_validade')
    paginator = Paginator(validades_qs, int(per_page))
    page_obj = paginator.get_page(request.GET.get('page'))

    for p in page_obj.object_list:
        dias_restantes = (p.dt_validade - hoje).days
        p.dias_restantes = dias_restantes
        
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

        p.lancado_por_nome = p.usuario_cadastro.first_name if p.usuario_cadastro else 'Sistema'

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
        return JsonResponse({'status': 'success'})
        
    return JsonResponse({'status': 'error', 'message': 'Método inválido'}, status=400)

@login_required
@checa_multiplos_grupos_403(['Administrador', 'Diretoria', 'Gerente de Loja', 'Gerente Distrital'])
def inativar_validade(request, id):
    if request.method == 'POST':
        Validade.objects.filter(id=id).update(ativo=False, usuario_ultimo=request.user)
        return JsonResponse({'status': 'success'})
        
    return JsonResponse({'status': 'error', 'message': 'Método inválido'}, status=400)


@login_required
@checa_multiplos_grupos_403(['Administrador', 'Diretoria', 'Gerente de Loja', 'Gerente Distrital', 'Atendente/Vendedor', 'Comprador'])
def ruptura_list(request):
    perfil = request.user.perfil
    lojas_permitidas = perfil.get_lojas_acessiveis()

    filtro_status = request.GET.get('status', '').strip()
    filtro_loja = request.GET.get('loja', '').strip()
    query = request.GET.get('q', '').strip()
    per_page = request.GET.get('per_page', '50')
    if per_page not in ['50', '100', '200', '500']:
        per_page = '50'

    rupturas_qs = Ruptura.objects.filter(
        loja_id__in=lojas_permitidas
    ).select_related('produto', 'loja_id', 'criado_por')

    if filtro_loja:
        rupturas_qs = rupturas_qs.filter(loja_id__cod_loja=filtro_loja)

    if filtro_status:
        rupturas_qs = rupturas_qs.filter(status=filtro_status)

    if query:
        rupturas_qs = rupturas_qs.filter(
            Q(produto__desc_produto__icontains=query) |
            Q(produto__cod_produto__icontains=query) |
            Q(produto__cod_gtin_principal__icontains=query) |
            Q(observacao_loja__icontains=query)
        )

    rupturas_qs = rupturas_qs.order_by('-data_cadastro')
    paginator = Paginator(rupturas_qs, int(per_page))
    page_obj = paginator.get_page(request.GET.get('page'))

    hoje = timezone.now()
    for r in page_obj.object_list:
        if r.data_cadastro:
            delta = hoje - r.data_cadastro
            r.dias_cadastrado = delta.days
        else:
            r.dias_cadastrado = 0

    # Uso da função centralizada para definir a permissão no template
    e_gestor_ou_comprador = usuario_e_gestor_ou_comprador(request.user)

    lojas_acesso = Loja.objects.filter(cod_loja__in=lojas_permitidas.values_list('cod_loja', flat=True)).order_by('cod_loja')

    context = {
        'page_obj': page_obj,
        'rupturas': page_obj.object_list,
        'lojas_acesso': lojas_acesso,
        'e_gestor_ou_comprador': e_gestor_ou_comprador,
        'filtro_status': filtro_status,
        'filtro_loja': filtro_loja,
        'query': query,
        'per_page': int(per_page),
    }

    return render(request, 'rupturas.html', context)

@login_required
def cadastrar_ruptura(request):
    if request.method == 'POST':
        produto_id = request.POST.get('produto_id')
        loja_id = request.POST.get('loja') or request.POST.get('loja_id')
        quantidade = request.POST.get('quantidade')
        observacao = request.POST.get('observacao_loja', '')

        if produto_id and quantidade and loja_id:
            produto = get_object_or_404(Produto, pk=produto_id)
            
            try:
                loja = Loja.objects.get(pk=loja_id)
            except (Loja.DoesNotExist, ValueError):
                loja = get_object_or_404(Loja, cod_loja=loja_id)

            Ruptura.objects.create(
                produto=produto,
                loja_id=loja,
                quantidade_necessaria=quantidade,
                observacao_loja=observacao,
                criado_por=request.user
            )
            messages.success(request, "Ruptura cadastrada com sucesso!")
        else:
            messages.error(request, "Preencha todos os campos obrigatórios, incluindo a loja e o produto.")

    return redirect('ruptura_list')

@login_required
def buscar_produtos_ajax(request):
    term = request.GET.get('q', '')
    produtos = Produto.objects.filter(desc_produto__icontains=term) | Produto.objects.filter(cod_produto__icontains=term) | Produto.objects.filter(cod_gtin_principal__icontains=term)
    data = [{'id': p.id, 'codigo': p.codigo, 'nome': p.nome} for p in produtos[:20]]
    return JsonResponse({'results': data})

@login_required
def atualizar_status_ruptura(request):
    if request.method == 'POST':
        e_gestor_ou_comprador = usuario_e_gestor_ou_comprador(request.user)

        ruptura_id = request.POST.get('ruptura_id')
        novo_status = request.POST.get('novo_status')
        obs_comprador = request.POST.get('observacao_comprador')
        obs_loja = request.POST.get('observacao_loja')

        ruptura = get_object_or_404(Ruptura, id=ruptura_id)

        # TRAVA RÍGIDA DE SEGURANÇA NO BACKEND:
        # Se NÃO for Gestor/Comprador:
        # 1. A ruptura DEVE estar no status 'RESOLVIDO'
        # 2. O novo status enviado só pode ser 'FINALIZADO' ou 'EM_ABERTO' (reabertura pela loja)
        if not e_gestor_ou_comprador:
            if ruptura.status != 'RESOLVIDO' or novo_status not in ['FINALIZADO', 'EM_ABERTO']:
                messages.error(request, "Você não tem permissão para alterar o status desta ruptura.")
                return redirect('ruptura_list')

        # Aplicação das alterações permitidas
        if novo_status:
            ruptura.status = novo_status
            
        # Apenas comprador/gestor pode preencher/alterar a observação do comprador
        if obs_comprador is not None and e_gestor_ou_comprador:
            ruptura.observacao_comprador = obs_comprador
            
        if obs_loja is not None:
            ruptura.observacao_loja = obs_loja

        ruptura.atualizado_por = request.user
        ruptura.save()
        messages.success(request, f"Status da Ruptura #{ruptura.id} atualizado para '{ruptura.get_status_display()}'!")

    return redirect('ruptura_list')