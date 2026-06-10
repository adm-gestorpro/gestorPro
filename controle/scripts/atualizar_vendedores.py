import requests, json, os

from dotenv import load_dotenv
from django.db.models.functions import Substr

from vendas.models import Vendedor

def atualiza_vendedores():
    currentPage = 0
    consulta = f'/crm/cadastro/vendedores'
    headers = {'Content-Type':'application/x-www-form-urlencoded', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': os.getenv('TOKEN_BLUESOFT')}
    filters = {'pageSize': 1000, 'currentPage': currentPage}
    json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':os.getenv('CLIENT_ID'), 'client_secret':os.getenv('CLIENT_SECRET')})
    request = requests.get(os.getenv('URL_BASE_API')+consulta, headers=headers, data=json_data, params=filters)
    dados = json.loads(request.text)

    for dado in dados['data']:
        for item in dado['informacoesDoVendedor']:
            consulta = Vendedor.objects.filter(id_operador=item['codigoIntegracao'])
            if not consulta:
                vendedor = Vendedor(
                    cod_vendedor=item['codigoIntegracao'],
                    id_operador=item['vendedorKey'],
                    nome_vendedor=dado['nomeRazao']
                )
                vendedor.save()