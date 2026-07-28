import os
import random
import threading
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse, QueryDict
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from controle.models import Loja
from produtos.models import Produto, Validade

# Importação dos scripts de sincronização externa / Supabase
from .scripts.atualizar_clientes import atualiza_clientes
from .scripts.atualizar_fornecedores import atualiza_fornecedores
from .scripts.atualizar_lojas_redes import atualiza_lojas, atualiza_redes
from .scripts.atualizar_produtos import atualiza_produtos
from .scripts.atualizar_vendas import atualiza_pedido_balcao, atualiza_vendas_online
from .scripts.atualizar_vendedores import atualiza_vendedores


def mensagem():
    hora = datetime.now().hour
    if 6 <= hora <= 11:
        return 'Bom dia'
    elif 12 <= hora <= 18:
        return 'Boa tarde'
    elif 19 <= hora <= 23:
        return 'Boa noite'
    return 'Boa madrugada'


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
            # Otimizado usando .values_list para evitar carregar objetos de grupo completos na memória
            if request.user.groups.filter(name__in=nomes_grupos).exists():
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return _wrapped_view
    return decorator


@never_cache
@ensure_csrf_cookie
def login_view(request):
    if request.method == 'POST':
        usuario = request.POST.get('username')
        senha = request.POST.get('password')
        request.session['user'] = usuario
        user = authenticate(request, username=usuario, password=senha)
        if user is not None:
            login(request, user)
            return redirect(dashboard)
        else:
            messages.error(request, "Usuário ou senha inválidos.") 
    return render(request, 'usuários/login.html')


def logout_user(request):
    logout(request)
    response = redirect('login_view')
    response.delete_cookie('csrftoken')
    return response

@login_required
def perfil_usuario(request):
    user = request.user

    if request.method == 'POST':
        if 'btn_atualizar_perfil' in request.POST:
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            if not email:
                messages.error(request, "O campo de e-mail não pode ficar vazio.")
            else:
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.save()
                messages.success(request, "Suas informações pessoais foram atualizadas com sucesso!")
                return redirect(perfil_usuario)

        elif 'btn_atualizar_senha' in request.POST:
            senha_atual = request.POST.get('current_password')
            nova_senha = request.POST.get('new_password')
            confirmar_senha = request.POST.get('confirm_password')

            if not user.check_password(senha_atual):
                messages.error(request, "A senha atual informada está incorreta.")
            
            elif nova_senha != confirmar_senha:
                messages.error(request, "A nova senha e a confirmação não coincidem.")
            
            elif len(nova_senha) < 8:
                messages.error(request, "A nova senha deve conter no mínimo 8 caracteres.")
            
            else:
                user.set_password(nova_senha)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Sua senha foi alterada com sucesso!")
                return redirect(perfil_usuario)

    return render(request, 'usuários/perfil.html', {'user': user})

@login_required
def configuracoes_usuario(request):
    return render(request, 'usuários/configuracoes.html')

@login_required
def logout_view(request):
    return render(request, 'usuários/logged_out.html')


@login_required
def service_worker(request):
    path = os.path.join(settings.BASE_DIR, 'controle/static/js/sw.js')
    with open(path, 'rb') as f:
        return HttpResponse(f.read(), content_type='application/javascript')


@login_required
def agenda(request):
    return render(request, 'agenda.html')


@login_required
def dashboard(request):
    usuario = request.session.get('user', request.user.username)
    context = {'user': usuario, 'mensagem': mensagem()}
    return render(request, 'dashboard.html', context)


@login_required
@checa_multiplos_grupos_403(['Administrador'])
def atualizacoes(request):
    usuario = request.session.get('user', request.user.username)
    context = {'user': usuario, 'mensagem': mensagem()}
    return render(request, 'atualizacoes.html', context)


# =========================================================================
# ROTAS DE ATUALIZAÇÃO OTIMIZADAS COM THREADS (CARREGAMENTO INSTANTÂNEO)
# =========================================================================

@login_required
@checa_multiplos_grupos_403(['Administrador'])
def atualizar_redes(request):
    if request.method == 'POST':
        # Dispara a função em segundo plano. O Django não espera terminar e responde na hora.
        threading.Thread(target=atualiza_redes).start()
        messages.info(request, "A atualização de redes foi iniciada em segundo plano.")
    return redirect(atualizacoes)


@login_required
@checa_multiplos_grupos_403(['Administrador'])
def atualizar_lojas(request):
    if request.method == 'POST':
        threading.Thread(target=atualiza_lojas).start()
        messages.info(request, "A atualização de lojas foi iniciada em segundo plano.")
    return redirect(atualizacoes)


@login_required
@checa_multiplos_grupos_403(['Administrador'])
def atualizar_produtos(request):
    if request.method == 'POST':
        threading.Thread(target=atualiza_produtos).start()
        messages.info(request, "A atualização de produtos foi iniciada em segundo plano.")
    return redirect(atualizacoes)


@login_required
@checa_multiplos_grupos_403(['Administrador'])
def atualizar_clientes(request):
    if request.method == 'POST':
        threading.Thread(target=atualiza_clientes).start()
        messages.info(request, "A atualização de clientes foi iniciada em segundo plano.")
    return redirect(atualizacoes)


@login_required
@checa_multiplos_grupos_403(['Administrador'])
def atualizar_fornecedores(request):
    if request.method == 'POST':
        threading.Thread(target=atualiza_fornecedores).start()
        messages.info(request, "A atualização de fornecedores foi iniciada em segundo plano.")
    return redirect(atualizacoes)


@login_required
@checa_multiplos_grupos_403(['Administrador'])
def atualizar_vendedores(request):
    if request.method == 'POST':
        threading.Thread(target=atualiza_vendedores).start()
        messages.info(request, "A atualização de vendedores foi iniciada em segundo plano.")
    return redirect(atualizacoes)


@login_required
@checa_multiplos_grupos_403(['Administrador'])
def atualizar_venda_online(request):
    if request.method == 'POST':
        threading.Thread(target=atualiza_vendas_online).start()
        messages.info(request, "A atualização de vendas online foi iniciada em segundo plano.")
    return redirect(atualizacoes)


@login_required
@checa_multiplos_grupos_403(['Administrador'])
def atualizar_pedido_balcao(request):
    if request.method == 'POST':
        threading.Thread(target=atualiza_pedido_balcao).start()
        messages.info(request, "A atualização de pedidos de balcão foi iniciada em segundo plano.")
    return redirect(atualizacoes)


# =========================================================================
# ROTA DE PEDIDOS (MOCK DATA PREPARADO PARA PERFORMANCE REAIS)
# =========================================================================

@login_required
def pedido(request):
    produtos = []
    
    descricoes = [
        "Ração Golden Formula Cães Adultos Frango 15kg",
        "Ração Premier Nutrição Clínica Renal Cães 2kg",
        "Areia Higiênica Pipicat Floral 4kg",
        "Antipulgas Bravecto Cães 10 a 20kg",
        "Tapete Higiênico Super Secão 30 Unidades",
        "Sachê Royal Canin Gatos Castrados 85g",
        "Shampoo Sanol Dog Pelos Claros 500ml",
        "Brinquedo Mordedor Osso Maciço Borracha M",
        "Coleira Antipulgas Seresto Cães acima 8kg",
        "Ração Whiskas Carne para Gatos Adultos 10,1kg"
    ]

    lojas_codes = ["LJ01", "LJ02", "LJ03", "LJ04", "LJ05"]

    for i in range(1, 3):
        peso = round(random.uniform(0.1, 15.0), 2)
        preco_base = round(random.uniform(10.0, 300.0), 2)
        margem = 36.8
        imp_est = 19
        imp_fed = 9.25
        
        # FÓRMULA DE MARGEM PRECISA
        divisor = (1 - ((margem + imp_fed * (1 - imp_est / 100) + imp_est) / 100))
        preco_venda = round(preco_base / divisor, 2) if divisor > 0 else 0

        lojas_data = []
        for loja in lojas_codes:
            v30 = random.randint(0, 50)
            v60 = random.randint(0, 50)
            v90 = random.randint(0, 50)
            
            lojas_data.append({
                "codigo": loja,
                "sugestao": random.randint(0, 20),
                "est_total": random.randint(0, 100),
                "est_disp": random.randint(0, 80),
                "est_res": random.randint(0, 10),
                "est_bloq": random.randint(0, 5),
                "pend_rec": random.randint(0, 20),
                "venda_30d": v30,
                "venda_60d": v60,
                "venda_90d": v90,
                "media": round((v30 + v60 + v90) / 3, 2),
                "reposicao": random.randint(1, 15),
                "ult_ent": random.randint(0, 50),
                "data_ent": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%d/%m/%Y"),
                "ult_sai": random.randint(0, 20),
                "data_sai": (datetime.now() - timedelta(days=random.randint(0, 5))).strftime("%d/%m/%Y"),
                "margem_sai": random.randint(10, 40)
            })

        produtos.append({
            "id": i,
            "desc": descricoes[i-1],
            "fab": f"REF{random.randint(1000, 9999)}",
            "ean": f"789{random.randint(100000000, 999999999)}",
            "emb": random.choice(["UN", "CX", "FD"]),
            "peso": peso,
            "preco": preco_base,
            "margem": margem,
            "preco_venda": preco_venda,
            "lojas": lojas_data,
            "imp_fed": imp_fed,
            "imp_est": imp_est
        })

    context = {
        'produtos': produtos, 
        'fornecedor': 'NUTRIAVE ALIMENTOS', 
        'linha_compra': 'NUTRIAVE - ATALAIA', 
        'divisao_compra': 1, 
        'comprador': 'BRUNO NASCIMENTO'
    }
    return render(request, 'pedido.html', context)