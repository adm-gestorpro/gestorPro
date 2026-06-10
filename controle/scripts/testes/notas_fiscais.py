import requests, json

client_id = ''
client_secret = ''
token = ''
url_base_api = 'https://erp.bluesoft.com.br/agromixatalaia/api'
url_base_oauth2 = 'https://erp.bluesoft.com.br/agromixatalaia/oauth2'
currentPage = 0
consulta = f'/estoques/notas-fiscais'
headers = {'Content-Type': 'application/json', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': token}
json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':client_id, 'client_secret':client_secret})
filters = {'pageSize': 1000, 'currentPage': currentPage, 'tipoNota': 'ENTRADA', 'cpfCnpjFornecedor': '27250737000542', 'lojaKey': 206, 'nfChave': '32260427250737000542550010013452291192705338'}
request = requests.get(url_base_api+consulta, headers=headers, data=json_data, params=filters)
dados = json.loads(request.text)['data']

for dado in dados:
    print(f'\n\n\n ###########     Nova Entrada     ################')
    for itens in dado['itens']:
        for chave, valor in itens.items():
            if itens['produtoKey'] == 14998:
                print(f'{chave} => {valor}')