import requests
import xml.etree.ElementTree as ET

from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from produtos.models import Produto
from controle.models import Loja, Rede

from controle.scripts.consulta_pedido_nf import consulta_nfe_bluesoft, consulta_pedido_compra_bluesoft


def normalizar_codigo(codigo):
    """Remove zeros à esquerda e espaços para permitir cruzamento exato."""
    if not codigo:
        return ""
    return str(codigo).strip().lstrip('0')


def baixar_xml_da_url(url_download):
    resposta = requests.get(url_download, timeout=10)
    resposta.raise_for_status() 
    return resposta.content


def extrair_itens_nfe(xml_content):
    """
    Lê o arquivo XML/String da NF-e e extrai apenas os produtos, quantidades 
    e valores das tags <det>, ignorando totalmente qualquer tag de pedido externo (xPed).
    """
    if isinstance(xml_content, str):
        xml_content = xml_content.encode('utf-8')

    root = ET.fromstring(xml_content)
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    itens = []

    dets = root.findall('.//nfe:det', ns) or root.findall('.//det')

    for det in dets:
        prod = det.find('nfe:prod', ns) if det.find('nfe:prod', ns) is not None else det.find('prod')
        
        if prod is not None:
            c_prod = prod.findtext('nfe:cProd', '', ns) or prod.findtext('cProd', '')
            c_ean = prod.findtext('nfe:cEAN', '', ns) or prod.findtext('cEAN', '')
            x_prod = prod.findtext('nfe:xProd', '', ns) or prod.findtext('xProd', '')
            q_com = float(prod.findtext('nfe:qCom', '0', ns) or prod.findtext('qCom', '0'))
            v_un_com = float(prod.findtext('nfe:vUnCom', '0', ns) or prod.findtext('vUnCom', '0'))

            if not c_ean or c_ean.strip().upper() == 'SEMGTIN':
                c_ean = c_prod.strip()

            itens.append({
                'codigo_fornecedor': c_prod.strip(),
                'ean': c_ean.strip(),
                'descricao': x_prod.strip(),
                'qtd_nf': q_com,
                'valor_nf': v_un_com,
            })

    return itens


def comparar_pedido_nfe(pedido_api, itens_nfe, loja_selecionada=None):
    """
    Cruza os itens do Pedido de Compra da API com o XML da NF-e.
    Garante isolamento absoluto de quantidades por produto.
    """
    if isinstance(pedido_api, list) and len(pedido_api) > 0:
        pedido_data = pedido_api[0]
    else:
        pedido_data = pedido_api or {}

    itens_api_brutos = pedido_data.get('itens', [])

    # 1. Filtro de Filial/Loja
    if loja_selecionada:
        itens_api = [
            item for item in itens_api_brutos
            if str(item.get('codigoLoja', '')).strip() == str(loja_selecionada).strip()
        ]
    else:
        itens_api = itens_api_brutos

    INVALIDOS = {'', 'NONE', 'NULL', 'SEMGTIN', 'SEM GTIN', '0', '0000000000000'}

    # ETAPA 1: Processamento isolado dos itens do pedido (Sem somar produtos distintos)
    itens_pedido_lista = []

    for item in itens_api:
        qtd_ped = float(item.get('quantidadeSolicitada', 0.0))
        custo_ped = float(item.get('custoBrutoEmbalagem', 0.0))
        
        produto_key_raw = str(item.get('produtoKey', '')).strip() if item.get('produtoKey') else ''
        produto_key = produto_key_raw if produto_key_raw.upper() not in INVALIDOS else None
        
        ean_raw = (
            item.get('codigoEan') or 
            item.get('codigoEanUnitario') or 
            item.get('ean') or 
            item.get('gtin') or 
            item.get('codigoBarras') or ''
        )
        ean_api = str(ean_raw).strip()
        ean_valido = ean_api if ean_api.upper() not in INVALIDOS else None

        # Busca segura no Banco de Dados local
        produto_db = None
        filters = Q()
        if produto_key:
            filters |= Q(pk=produto_key) | Q(cod_produto=produto_key)
        if ean_valido:
            filters |= Q(cod_gtin_principal=ean_valido) | Q(cod_gtins_disponiveis__icontains=ean_valido)

        if filters:
            produto_db = Produto.objects.filter(filters).first()

        # Coleta APENAS chaves estritamente exclusivas do produto
        chaves_item = set()
        
        if produto_key:
            chaves_item.add(produto_key)
            norm_pk = normalizar_codigo(produto_key)
            if norm_pk: chaves_item.add(norm_pk)

        if ean_valido:
            chaves_item.add(ean_valido)
            norm_ean = normalizar_codigo(ean_valido)
            if norm_ean: chaves_item.add(norm_ean)

        if produto_db:
            db_cod = getattr(produto_db, 'cod_produto', None)
            if db_cod and str(db_cod).strip().upper() not in INVALIDOS:
                s_cod = str(db_cod).strip()
                chaves_item.add(s_cod)
                norm_cod = normalizar_codigo(s_cod)
                if norm_cod: chaves_item.add(norm_cod)

            db_gtin = getattr(produto_db, 'cod_gtin_principal', None)
            if db_gtin and str(db_gtin).strip().upper() not in INVALIDOS:
                s_gtin = str(db_gtin).strip()
                chaves_item.add(s_gtin)
                norm_gtin = normalizar_codigo(s_gtin)
                if norm_gtin: chaves_item.add(norm_gtin)

            db_gtins_lista = getattr(produto_db, 'cod_gtins_disponiveis', [])
            if isinstance(db_gtins_lista, list):
                for gtin_extra in db_gtins_lista:
                    s_extra = str(gtin_extra).strip() if gtin_extra else ''
                    if s_extra.upper() not in INVALIDOS:
                        chaves_item.add(s_extra)
                        norm_ex = normalizar_codigo(s_extra)
                        if norm_ex: chaves_item.add(norm_ex)

            # Apenas referências de SKU do item (removido 'codigo_fornecedor' para evitar colisão)
            for campo_sku in ['referencia_fornecedor', 'sku']:
                val_sku = getattr(produto_db, campo_sku, None)
                if val_sku and str(val_sku).strip().upper() not in INVALIDOS:
                    s_sku = str(val_sku).strip()
                    chaves_item.add(s_sku)
                    norm_sku = normalizar_codigo(s_sku)
                    if norm_sku: chaves_item.add(norm_sku)

        chaves_finais = {c for c in chaves_item if c and c.upper() not in INVALIDOS}

        # Verifica se É EXATAMENTE O MESMO PRODUTO que já entrou antes no pedido
        item_existente = None
        for item_p in itens_pedido_lista:
            if (produto_key and item_p['produto_key'] == produto_key) or \
               (ean_valido and item_p['ean_api'] == ean_valido):
                item_existente = item_p
                break

        if item_existente:
            # Soma APENAS se for o mesmo produto (ex: entregas fracionadas)
            item_existente['qtd_pedido'] += qtd_ped
            item_existente['chaves'].update(chaves_finais)
        else:
            itens_pedido_lista.append({
                'produto_key': produto_key,
                'ean_api': ean_api,
                'descricao_produto': item.get('descricaoProduto', ''),
                'qtd_pedido': qtd_ped,
                'custo_pedido': custo_ped,
                'processado': False,
                'produto_db': produto_db,
                'chaves': chaves_finais
            })

    # ETAPA 2: Indexação para busca rápida pelo XML (Apenas mapeia leituras, NUNCA altera quantidades)
    mapa_pedido = {}
    for item_info in itens_pedido_lista:
        for chave in item_info['chaves']:
            if chave not in mapa_pedido:
                mapa_pedido[chave] = item_info

    # ETAPA 3: Confronto dos itens do XML da NF-e
    divergencias = []
    itens_corretos = []
    impacto_financeiro_total = 0.0

    for item_nfe in itens_nfe:
        cod_xml = item_nfe.get('codigo_fornecedor', '')
        cod_xml_key = normalizar_codigo(cod_xml) if cod_xml else ''
        ean_xml = str(item_nfe.get('ean', '')).strip()
        qtd_nf = float(item_nfe.get('qtd_nf', 0.0))
        vlr_nf = float(item_nfe.get('valor_nf', 0.0))

        item_ped = None
        if cod_xml_key and cod_xml_key.upper() not in INVALIDOS:
            item_ped = mapa_pedido.get(cod_xml_key)
        
        if not item_ped and cod_xml and str(cod_xml).strip().upper() not in INVALIDOS:
            item_ped = mapa_pedido.get(str(cod_xml).strip())
        
        if not item_ped and ean_xml and ean_xml.upper() not in INVALIDOS:
            item_ped = mapa_pedido.get(ean_xml)
            if not item_ped:
                item_ped = mapa_pedido.get(normalizar_codigo(ean_xml))

        if not item_ped:
            impacto = qtd_nf * vlr_nf
            impacto_financeiro_total += impacto

            divergencias.append({
                'codigo_fornecedor': cod_xml,
                'ean': ean_xml,
                'descricao': item_nfe.get('descricao', ''),
                'motivo_divergencia': "Produto faturado na NF-e não consta no Pedido de Compra",
                'qtd_nf': qtd_nf,
                'qtd_pedido': 0.0,
                'valor_nf': vlr_nf,
                'valor_pedido': 0.0
            })
            continue

        item_ped['processado'] = True
        qtd_ped = item_ped['qtd_pedido']
        vlr_ped = item_ped['custo_pedido']

        motivos = []

        if abs(qtd_nf - qtd_ped) > 0.0001:
            diferenca_qtd = qtd_nf - qtd_ped
            if diferenca_qtd > 0:
                impacto_financeiro_total += (diferenca_qtd * vlr_nf)
            motivos.append(f"Quantidade divergente (Faturado: {qtd_nf:.2f} / Pedido: {qtd_ped:.2f})")

        if abs(vlr_nf - vlr_ped) > 0.01:
            diferenca_vlr = (vlr_nf - vlr_ped) * qtd_nf
            if diferenca_vlr > 0:
                impacto_financeiro_total += diferenca_vlr
            motivos.append(f"Custo unitário divergente (NF: R$ {vlr_nf:.2f} / Pedido: R$ {vlr_ped:.2f})")

        if motivos:
            divergencias.append({
                'codigo_fornecedor': cod_xml,
                'ean': ean_xml,
                'descricao': item_nfe.get('descricao', ''),
                'motivo_divergencia': " | ".join(motivos),
                'qtd_nf': qtd_nf,
                'qtd_pedido': qtd_ped,
                'valor_nf': vlr_nf,
                'valor_pedido': vlr_ped
            })
        else:
            itens_corretos.append({
                'codigo_fornecedor': cod_xml,
                'ean': ean_xml,
                'descricao': item_nfe.get('descricao', ''),
                'quantidade': qtd_nf,
                'quantidade_pedido': qtd_ped,
                'preco_unitario': vlr_nf,
                'preco_pedido': vlr_ped
            })

    # ETAPA 4: Itens do pedido que NÃO vieram faturados no XML
    for item_ped in itens_pedido_lista:
        if not item_ped['processado']:
            produto_key = item_ped['produto_key']
            ean_api = item_ped['ean_api']
            produto_db = item_ped['produto_db']
            desc_api = item_ped['descricao_produto']
            
            if produto_db:
                descricao = getattr(produto_db, 'desc_produto', desc_api or f"Produto Key: {produto_key}")
                ean = getattr(produto_db, 'cod_gtin_principal', ean_api or 'N/A')
                codigo_exibicao = str(getattr(produto_db, 'cod_produto', produto_key)).strip()
                if codigo_exibicao.isdigit():
                    codigo_exibicao = codigo_exibicao.lstrip('0') or '0'
            else:
                descricao = desc_api or f"Produto Key: {produto_key or ean_api} (Não Faturado)"
                ean = ean_api if ean_api else 'N/A'
                codigo_exibicao = str(produto_key).strip() if produto_key else 'N/A'
                if codigo_exibicao.isdigit():
                    codigo_exibicao = codigo_exibicao.lstrip('0') or '0'

            divergencias.append({
                'codigo_fornecedor': codigo_exibicao,
                'ean': ean,
                'descricao': descricao,
                'motivo_divergencia': "Consta no Pedido de Compra mas NÃO veio na NF-e",
                'qtd_nf': 0.0,
                'qtd_pedido': item_ped['qtd_pedido'],
                'valor_nf': 0.0,
                'valor_pedido': item_ped['custo_pedido']
            })

    return {
        'numero_pedido': pedido_data.get('numeroPedido'),
        'status_pedido': pedido_data.get('statusPedido'),
        'total_itens': len(itens_nfe),
        'total_divergencias': len(divergencias),
        'total_corretos': len(itens_corretos),
        'impacto_financeiro_total': impacto_financeiro_total,
        'divergencias': divergencias,
        'itens_corretos': itens_corretos
    }


@login_required
def conciliacao(request):
    # 1. Carrega as lojas que o usuário tem permissão (RBAC do GestorPro)
    # Ajuste o filtro abaixo conforme a lógica de relacionamento do seu User com as Lojas
    if hasattr(request.user, 'lojas_permitidas'):
        lojas_usuario = request.user.lojas_permitidas.all()
    else:
        lojas_usuario = Loja.objects.all().order_by('cod_loja') # Fallback genérico

    context = {
        'lojas': lojas_usuario
    }

    if request.method == 'POST':
        # Recebe os pedidos (pode ser "87715" ou "87715, 87716, 87717")
        pedidos_str = request.POST.get('numero_pedido', '').strip()
        chave_acesso = request.POST.get('chave_acesso', '').strip()
        loja_selecionada = request.POST.get('loja', '').strip()
        xml_file = request.FILES.get('xml_file')

        try:
            # Transforma a string em uma lista limpa de números
            numeros_pedidos = [n.strip() for n in pedidos_str.replace(';', ',').split(',') if n.strip()]
            
            itens_consolidados = []
            pedidos_encontrados = []
            status_pedidos = set()

            # 2. Consulta a API para CADA pedido digitado e consolida os itens
            for num in numeros_pedidos:
                api_response = consulta_pedido_compra_bluesoft(num, loja_selecionada)
                
                # A API retorna uma lista, iteramos sobre ela
                lista_pedidos_api = api_response if isinstance(api_response, list) else [api_response]
                
                for ped in lista_pedidos_api:
                    if not ped: 
                        continue
                    
                    # Filtra: Ignora o pedido se a loja for diferente da selecionada no combo
                    if loja_selecionada and str(ped.get('lojaKey')) != str(loja_selecionada):
                        continue
                        
                    itens_consolidados.extend(ped.get('itens', []))
                    
                    if ped.get('numeroPedido'):
                        pedidos_encontrados.append(str(ped.get('numeroPedido')))
                    if ped.get('statusPedido'):
                        status_pedidos.add(str(ped.get('statusPedido')))

            # Se depois de filtrar não sobrar nada
            if not itens_consolidados:
                messages.warning(request, "Nenhum item encontrado para os pedidos informados na loja selecionada.")
                return render(request, 'conciliacao.html', context)

            # 3. Cria um "Pedido Consolidado" com o formato exato que a API retorna
            # para não precisarmos alterar a lógica matemática do comparar_pedido_nfe
            dados_pedido_api = [{
                # Une os números sem repetir
                'numeroPedido': ", ".join(list(dict.fromkeys(pedidos_encontrados))), 
                'statusPedido': " / ".join(status_pedidos) if status_pedidos else 'DESCONHECIDO',
                'itens': itens_consolidados
            }]
            
            # 4. Obtenção do XML da NF-e
            if chave_acesso and not xml_file:
                chave_acesso_api = consulta_nfe_bluesoft(chave_acesso)
                xml_content = baixar_xml_da_url(chave_acesso_api)
            elif xml_file:
                xml_content = xml_file.read()
            else:
                xml_content = None

            if not xml_content:
                messages.error(request, "XML da NF-e não foi localizado.")
                return render(request, 'conciliacao.html', context)

            # 5. Processamento e Cruzamento
            itens_nfe = extrair_itens_nfe(xml_content)
            analise = comparar_pedido_nfe(dados_pedido_api, itens_nfe, loja_selecionada)

            context.update({
                'sucesso': True,
                'pedido_id': dados_pedido_api[0]['numeroPedido'],
                'loja_selecionada': loja_selecionada,
                'pedidos_input': pedidos_str, # Mantém o que o usuário digitou no form
                'analise': analise,
            })

        except Exception as e:
            messages.error(request, f"Erro ao processar conciliação: {str(e)}")

    return render(request, 'conciliacao.html', context)