import requests, json

client_id = ''
client_secret = ''
token = ''
url_base_api = 'https://erp.bluesoft.com.br/agromixatalaia/api'
url_base_oauth2 = 'https://erp.bluesoft.com.br/agromixatalaia/oauth2'
currentPage = 0
consulta = f'/estoques/movimentacoesdeestoque/analitico'
headers = {'Content-Type': 'application/json', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': token}
json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':client_id, 'client_secret':client_secret})
filters = {'pageSize': 1000, 'currentPage': currentPage, 'dataMovimento': '07/04/2026', 'produtoKey': 14998, 'lojaKey': 206}
request = requests.get(url_base_api+consulta, headers=headers, data=json_data, params=filters)
dados = json.loads(request.text)['data']

custo_icms = 0
custo_contabil = 0

valor_pis = 0
valor_cofins = 0
valor_ipi = 0
valor_icms = 0

qt_compra = 0

aliquota_icms = 0
aliquota_ipi = 0
aliquota_pis = 0
aliquota_cofins = 0

preco_compra = 0

frete = 9.84
iva = 0.6263


#print(dados)


for dado in dados:
    for chave, valor in dado.items():
        if dado['tipoMovimento'] == 'Compra':
            qt_compra = dado['quantidade']

            custo_icms = dado['custoEstoqueComIcm']
            custo_contabil = dado['custoContabil']

            aliquota_icms = dado['icmsAliquota']
            aliquota_ipi = dado['ipiAliquota']
            aliquota_pis = dado['pisAliquota']
            aliquota_cofins = dado['cofinsAliquota']

            valor_icms = dado['icmsValor']
            valor_ipi = dado['valorIpi']/qt_compra
            valor_pis = dado['pisValor']/qt_compra
            valor_cofins = dado['cofinsValor']/qt_compra


for dado in dados:
    for chave, valor in dado.items():
        if dado['tipoMovimento'] == 'Crédito de Impostos Recuperáveis sobre o frete':
            if custo_icms >= dado['custoEstoqueComIcm']:
                custo_icms = dado['custoEstoqueComIcm']
            if custo_contabil >= dado['custoContabil']:
                custo_contabil = dado['custoContabil']


preco_compra = (custo_contabil + valor_pis + valor_cofins - frete)/(1 - 0.19 + (0.19 * 1.6263) + (0.02 * 1.6263))


print(f'Quantidade de compra: {qt_compra}')

print(f'Alíquota ICMS: {aliquota_icms}')
print(f'Alíquota IPI: {aliquota_ipi}')
print(f'Alíquota PIS: {aliquota_pis}')
print(f'Alíquota COFINS: {aliquota_cofins}')

print(f'Valor do ICMS: {valor_icms}')
print(f'Valor do IPI: {valor_ipi}')
print(f'Valor do PIS: {valor_pis}')
print(f'Valor do COFINS: {valor_cofins}')

print(f'Custo do estoque com ICMS: {custo_icms}')
print(f'Custo contábil: {custo_contabil}')

print(f'Preço de compra: {preco_compra}')
