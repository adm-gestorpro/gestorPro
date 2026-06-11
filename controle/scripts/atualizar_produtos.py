import requests, json, os

from dotenv import load_dotenv
from django.db.models.functions import Substr

from produtos.models import Produto

def atualiza_produtos():
    flag = 0
    novos = 0
    atualizados = 0
    currentPage = 0
    while flag == 0:
        tipoProduto = 'VENDA'
        consulta_api = f'{os.getenv('URL_BASE_API')}/comercial/produtos'
        headers = {'Content-Type':'application/x-www-form-urlencoded', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': os.getenv('TOKEN_BLUESOFT')}
        json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':os.getenv('CLIENT_ID'), 'client_secret':os.getenv('CLIENT_SECRET')})  
        filters = {'tipoProduto': tipoProduto, 'pageSize': 1000, 'currentPage': currentPage}
        request = requests.get(consulta_api, headers=headers, data=json_data, params=filters)
        dados = json.loads(request.text)
        if dados['data']:
            currentPage += 1
            for dado in dados['data']:
                consulta = Produto.objects.filter(cod_produto=dado['produtoKey'])
                if not consulta:
                    novos += 1
                    produto = Produto(
                        cod_produto = dado['produtoKey'],
                        desc_produto = dado['descricao'],
                        cod_gtin_principal = dado['gtinPrincipal'],
                        cod_gtins_disponiveis = dado['gtins'],
                        dt_cadastro = dado['dataCadastro'],
                        dt_ult_alteracao = dado['ultimaAlteracao'],
                        status_produto = dado['status'],
                        desc_marca = dado.get('marca', ''),
                        caixa = dado['caixa']
                    )
                    produto.save()
                else:
                    atualizados += 1
                    Produto.objects.filter(cod_produto=dado['produtoKey']).update(
                        desc_produto = dado['descricao'],
                        cod_gtin_principal = dado['gtinPrincipal'],
                        cod_gtins_disponiveis = dado['gtins'],
                        dt_cadastro = dado['dataCadastro'],
                        dt_ult_alteracao = dado['ultimaAlteracao'],
                        status_produto = dado['status'],
                        desc_marca = dado.get('marca', ''),
                        caixa = dado['caixa']
                    )
        else:
            flag = 1
            
    return 0