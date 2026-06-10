import requests, json

client_id = ''
client_secret = ''
token = ''
url_base_api = 'https://erp.bluesoft.com.br/agromixatalaia/api'
url_base_oauth2 = 'https://erp.bluesoft.com.br/agromixatalaia/oauth2'
currentPage = 0
consulta = f'/vendas/precos/packvirtual'
headers = {'Content-Type':'application/x-www-form-urlencoded', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': token}
json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':client_id, 'client_secret':client_secret})

filters = {'pageSize': 1000, 'currentPage': currentPage, 'lojaKey': [201,202,203,204,205], 'vigente': 'SIM'}
request = requests.get(url_base_api+consulta, headers=headers, data=json_data, params=filters)
dados = json.loads(request.text)['data']

for dado in dados:
    print('\nPack')
    for key, value in dado.items():
        print(f'{key}: {value} - Tipo: {type(value)}')