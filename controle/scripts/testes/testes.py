import requests, json

client_id = ''
client_secret = ''
token = ''
url_base_api = 'https://erp.bluesoft.com.br/agromixatalaia/api'
url_base_oauth2 = 'https://erp.bluesoft.com.br/agromixatalaia/oauth2'
currentPage = 0
#consulta = f'/estoques/notas-fiscais'
#consulta = f'/comercial/produtos'
consulta = f'/vendas/precos'
headers = {'Content-Type': 'application/json', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': token}
json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':client_id, 'client_secret':client_secret})
#filters = {'pageSize': 1000, 'currentPage': currentPage, 'lojaKey': 201, 'dataRecebimentoFinal': '26/03/2026', 'tipoNota': 'ENTRADA', 'nfChave': '29260361068276004940550080001238711932972574'}
#filters = {'pageSize': 1000, 'currentPage': currentPage, 'produtoKey': 34461} #34462
filters = {'pageSize': 1000, 'currentPage': currentPage, 'lojaKey': 201, 'dataAlteracaoInicio': '26/03/2026'} #34462
request = requests.get(url_base_api+consulta, headers=headers, data=json_data, params=filters)
dados = json.loads(request.text)['data']

for dado in dados:
    print(dado['produtoKey'])
