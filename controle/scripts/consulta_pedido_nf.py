import requests, json, os

from dotenv import load_dotenv
from django.db.models.functions import Substr

def consulta_nfe_bluesoft(nfChave):
    currentPage = 0
    consulta = f'/estoques/notas-fiscais/xml/{nfChave}'
    headers = {'Content-Type':'application/x-www-form-urlencoded', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': os.getenv('TOKEN_BLUESOFT')}
    json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':os.getenv('CLIENT_ID'), 'client_secret':os.getenv('CLIENT_SECRET')})
    filters = {'pageSize': 1000, 'currentPage': currentPage}
    request = requests.get(os.getenv('URL_BASE_API')+consulta, headers=headers, data=json_data, params=filters)
    dados = json.loads(request.text)
    if dados:
        return dados['URL_S3']


def consulta_pedido_compra_bluesoft(pedido, loja):
    currentPage = 0
    consulta = f'/compras/pedidos-de-compra/edi'
    headers = {'Content-Type':'application/x-www-form-urlencoded', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': os.getenv('TOKEN_BLUESOFT')}
    json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':os.getenv('CLIENT_ID'), 'client_secret':os.getenv('CLIENT_SECRET')})
    filters = {'pageSize': 1000, 'currentPage': currentPage, 'numeroDoPedido': pedido, 'pedidoEnviadoEdi': 'TODOS', 'lojaKey': loja}
    request = requests.get(os.getenv('URL_BASE_API')+consulta, headers=headers, data=json_data, params=filters)
    dados = json.loads(request.text)['data']
    if dados:
        return dados