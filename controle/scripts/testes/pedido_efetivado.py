import requests, json

client_id = ''
client_secret = ''
token = ''
url_base_api = 'https://erp.bluesoft.com.br/agromixatalaia/api'
url_base_oauth2 = 'https://erp.bluesoft.com.br/agromixatalaia/oauth2'
currentPage = 0
consulta = f'/compras/pedidos-de-compra'
headers = {'Content-Type': 'application/json', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': token}
json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':client_id, 'client_secret':client_secret})
filters = {'pageSize': 1000, 'currentPage': currentPage, 'dataEmissao': '01/10/2025'}
request = requests.get(url_base_api+consulta, headers=headers, data=json_data, params=filters)
dados = json.loads(request.text)['data']

for dado in dados:
    print(f'Pedido {dado['numeroPedido']} | Data de emissão: {dado['dataEmissao']} | Status: {dado['statusPedido']} | Fornecedor: {dado['fornecedorKey']}')