import requests, json, os

from dotenv import load_dotenv
from django.db.models.functions import Substr

from datetime import date, timedelta, datetime

from produtos.models import Produto
from controle.models import Loja


def consulta_preco(produto, loja):
    consulta_api = f'/vendas/precos'
    headers = {'Content-Type':'application/x-www-form-urlencoded', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': os.getenv('TOKEN_BLUESOFT')}
    json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':os.getenv('CLIENT_ID'), 'client_secret':os.getenv('CLIENT_SECRET')})
    currentPage = 0
    filters = {'pageSize': 1000, 'currentPage': currentPage, 'lojaKey': loja.cod_loja, 'produtoKey': produto.cod_produto}
    request = requests.get(os.getenv('URL_BASE_API')+consulta_api, headers=headers, data=json_data, params=filters)
    dados = json.loads(request.text)['data']

    if dados:
        for dado in dados:
            estoque = {'cod_produto': dado['produtoKey'], 'cod_loja': dado['lojaKey'], 'preco_venda': dado['precoVenda'], 'preco_oferta': dado.get('precoOferta','-'), 'vigencia_oferta': dado.get('dataFinalOferta','-')}
            return estoque