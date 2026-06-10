import requests, json, os

from dotenv import load_dotenv
from django.db.models.functions import Substr

from datetime import date, timedelta, datetime

from vendas.models import Faturamento, Vendedor
from produtos.models import Produto
from controle.models import Loja

def atualiza_vendas_online():
    consulta_api = f'/vendas/vendaonline'
    headers = {'Content-Type':'application/x-www-form-urlencoded', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': os.getenv('TOKEN_BLUESOFT')}
    json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':os.getenv('CLIENT_ID'), 'client_secret':os.getenv('CLIENT_SECRET')})

    lojas = Loja.objects.all()
    for loja in lojas:
        print(f'Loja: {loja.cod_loja}')
        currentPage = 0
        flag = 0
        while flag == 0:
            filters = {'pageSize': 1000, 'currentPage': currentPage, 'lojaKey': loja.cod_loja}
            request = requests.get(os.getenv('URL_BASE_API')+consulta_api, headers=headers, data=json_data, params=filters)
            dados = json.loads(request.text)['data']
            if dados:
                currentPage += 1
                for dado in dados:
                    consulta = Faturamento.objects.filter(modelo_doc=dado['modelo'], pedido_doc=dado['cupomFiscalKey'])
                    if not consulta:
                        vendedor = Vendedor.objects.get(cod_vendedor=dado.get('vendedor',0))
                        for item in dado['itens']:
                            produto = Produto.objects.get(cod_produto=item['produtoKey'])
                            faturamento = Faturamento(
                                id_produto=produto,
                                cod_loja=loja,
                                emissao_doc=datetime.strptime(dado['hora'], "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M"),
                                numero_doc=dado['cupomNumero'],
                                pedido_doc=dado['cupomFiscalKey'],
                                modelo_doc=dado['modelo'],
                                chave_doc=dado['chave'],
                                serie_doc=dado['serie'],
                                equipamento_doc=dado['ecf'],
                                operador=dado['numeroOperador'],
                                vendedor=vendedor,
                                ean_fat=item['barraKey'],
                                qt_fat=item['quantidadeVendida'],
                                valor_venda=item['valorVendido'],
                                status_doc=dado['cancelado'],
                                obs_geral=''
                            )
                            faturamento.save()
                    else:
                        pass

            else:
                print(f'cheguei na página {currentPage}')
                flag = 1


def atualiza_pedido_balcao():
    temp_prod = 0
    temp_gtin = ''
    consulta_api = f'/venda/pedidovenda'
    headers = {'Content-Type':'application/x-www-form-urlencoded', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': os.getenv('TOKEN_BLUESOFT')}
    json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':os.getenv('CLIENT_ID'), 'client_secret':os.getenv('CLIENT_SECRET')})

    lojas = Loja.objects.all()
    for loja in lojas:
        print(f'Loja: {loja.cod_loja}')
        currentPage = 0
        flag = 0
        while flag == 0:
            filters = {'pageSize': 1000, 'currentPage': currentPage, 'lojaKey': loja.cod_loja, 'pedidoVendaStatus': ['FATURADO_POR_NOTA_FISCAL']}
            request = requests.get(os.getenv('URL_BASE_API')+consulta_api, headers=headers, data=json_data, params=filters)
            dados = json.loads(request.text)['data']
            if dados:
                currentPage += 1
                for dado in dados:
                    consulta = Faturamento.objects.filter(modelo_doc=55, pedido_doc=dado['pedidoVendaKey'])
                    if not consulta:
                        print(dado)
                        vendedor = Vendedor.objects.get(id_operador=dado.get('vendedorKey',0))
                        for item in dado['itens']:
                            for chave,valor in item['produto'].items():
                                if chave == 'produtoKey':
                                    temp_prod = valor
                                if chave == 'gtinPrincipal':
                                    temp_gtin = valor
                                
                                produto = Produto.objects.get(cod_produto=temp_prod)
                                faturamento = Faturamento(
                                    id_produto=produto,
                                    cod_loja=loja,
                                    emissao_doc=datetime.strptime(dado['dataEmissao'], "%d/%m/%Y").strftime("%Y-%m-%d %H:%M"),
                                    numero_doc=0,
                                    pedido_doc=dado['pedidoVendaKey'],
                                    modelo_doc=55,
                                    chave_doc=0,
                                    serie_doc=0,
                                    equipamento_doc=0,
                                    operador=0,
                                    vendedor=vendedor,
                                    ean_fat=temp_gtin,
                                    qt_fat=item['quantidadeSeparada'],
                                    valor_venda=item['precoVenda'],
                                    status_doc=False,
                                    obs_geral=''
                                )
                                faturamento.save()
                    else:
                        pass

            else:
                print(f'cheguei na página {currentPage}')
                flag = 1