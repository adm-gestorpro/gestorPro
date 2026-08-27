'''
    Esse módulo serve para fazer consultas com a API BlueSOft e retornar dados 
    para construção de informações sobre o comparativo de produtos e seus atributos, 
    além de informar o estoque comercial, regras fiscais, margem de região e preços.
'''

import os
import json
import requests

headers = {
    'Content-Type':'application/x-www-form-urlencoded', 
    'Cookie':'OAUTH=OAUTH_240', 
    'X-Customtoken': os.getenv('TOKEN_BLUESOFT')
    }

json_data = json.dumps({
    'grant_type':'client_credentials', 
    'scope':'switch.read', 
    'client_id':os.getenv('CLIENT_ID'), 
    'client_secret':os.getenv('CLIENT_SECRET')
    })

TIMEOUT_REQUEST = 5


def consulta_produto(produto_key):
    '''
        Método para fazer a consulta de um produto e seus atributos

        Nesse método os campos interessantes são:
            - produtoKey
            - ncm
            - cest
            - tributacaoEstadual
            - pisConfisSaidaNaoCumulativo
    '''
    produto = ''
    current_page = 0
    tipo_produto = 'VENDA'
    consulta_api = f'{os.getenv('URL_BASE_API')}/comercial/produtos'
    filters = {
        'tipoProduto': tipo_produto, 
        'pageSize': 1000, 
        'currentPage': current_page, 
        'produtoKey': produto_key
        }
    request = requests.get(
        consulta_api,
        headers=headers,
        data=json_data,
        params=filters,
        timeout=TIMEOUT_REQUEST
        )
    dados = json.loads(request.text)
    if dados['data']:
        produto = dados['data']
    return produto


def consulta_margem_regiao(produto_key):
    '''
        Método para fazer a consulta da margem de um produto nas regiões cadastradas.

        Nesse método os campos interessantes são:
            - gtin
            - regiaoPrecoKey
            - margem
    '''
    margem = ''
    current_page = 0
    consulta_api = f'{os.getenv('URL_BASE_API')}/compras/cadastro/manutencao-margem-regioes-preco'
    filters = {
        'pageSize': 1000, 
        'currentPage': current_page, 
        'produtoKey': produto_key
        }
    request = requests.get(
        consulta_api,
        headers=headers,
        data=json_data,
        params=filters,
        timeout=TIMEOUT_REQUEST
        )
    dados = json.loads(request.text)
    if dados['data']:
        margem = dados['data']
    return margem


def consulta_regra_fiscal_produto(produto_key):
    '''
        Método para fazer a consulta da regra fiscal de um produto.

        Nesse método os campos interessantes são:
            - codigoFiguraFiscal
    '''
    regra_fiscal_produto = ''
    current_page = 0
    consulta_api = f'{os.getenv('URL_BASE_API')}/fiscal/figurafiscal/produto/{produto_key}'
    filters = {
        'pageSize': 1000, 
        'currentPage': current_page, 
        'produtoKey': produto_key
        }
    request = requests.get(
        consulta_api,
        headers=headers,
        data=json_data,
        params=filters,
        timeout=TIMEOUT_REQUEST
        )
    dados = json.loads(request.text)
    if dados['data']:
        regra_fiscal_produto = dados['data']
    return regra_fiscal_produto


def consulta_regra_fiscal_cadastro(codigo_figura_fiscal, uf_origem, uf_destino, tipo_regra):
    '''
        Método para consulta de regras fiscais e seus atributos.
        
        Nesse método os campos interessantes são:
            - regraFiscakKey
            - codigoFiguraFiscal
            - regraIcmsConsumidorFinal (icmsDetalhe: aliquotaFundoPobreza)
            - regraIpi (ipiDetalhamento: aliquota)
    '''
    regra_fiscal = ''
    current_page = 0
    consulta_api = f'{os.getenv('URL_BASE_API')}/fiscal/regrafiscal/completa'
    filters = {
        'pageSize': 1000,
        'currentPage': current_page,
        'codigoFiguraFiscal': codigo_figura_fiscal,
        'ativa': True,
        'ufOrigem': uf_origem,
        'ufDestino': uf_destino,
        'vigente': True,
        'tipoDeRegra': tipo_regra
        }
    request = requests.get(
        consulta_api,
        headers=headers,
        data=json_data,
        params=filters,
        timeout=TIMEOUT_REQUEST
        )
    dados = json.loads(request.text)
    if dados['data']:
        regra_fiscal = dados['data']
    return regra_fiscal


def consulta_estoque_comercial(produto_key):
    '''
        Método para consulta do estoque comercial de um produto.

        Nesse método os campos interessantes são:
            - produtoKey
            - lojaKey
            - custoMedioSemImposto
            - custoLiquidoUltimaCompra
    '''
    estoque_comercial = ''
    current_page = 0
    consulta_api = f'{os.getenv('URL_BASE_API')}/comercial/estoques'
    filters = {
        'pageSize': 1000,
        'currentPage': current_page,
        'produtoKey': produto_key,
        'retornarEstoqueEmTransito': True,
        'retornarDetalhesReservasLogisticas': True,
        'retornarCustoUltimaCompra': True
        }
    request = requests.get(
        consulta_api,
        headers=headers,
        data=json_data,
        params=filters,
        timeout=TIMEOUT_REQUEST
        )
    dados = json.loads(request.text)
    if dados['data']:
        estoque_comercial = dados['data']
    return estoque_comercial


def consulta_precos(produto_key):
    '''Método para consulta dos preços cadastrados de um produto'''
    precos = ''
    current_page = 0
    consulta_api = f'{os.getenv('URL_BASE_API')}/vendas/precos'
    filters = {
        'pageSize': 1000,
        'currentPage': current_page,
        'produtoKey': produto_key
    }
    request = requests.get(
        consulta_api,
        headers=headers,
        data=json_data,
        params=filters,
        timeout=TIMEOUT_REQUEST
        )
    dados = json.loads(request.text)
    if dados['data']:
        precos = dados['data']
    return precos
