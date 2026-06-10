import requests, json, os

from dotenv import load_dotenv
from django.db.models.functions import Substr

from fornecedores.models import Fornecedor

def atualiza_fornecedores():
    flag = 0
    novos = 0
    atualizados = 0
    currentPage = 0
    while flag == 0:
        consulta = f'{os.getenv('URL_BASE_API')}/fornecedores'
        headers = {'Content-Type':'application/x-www-form-urlencoded', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': os.getenv('TOKEN_BLUESOFT')}
        json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':os.getenv('CLIENT_ID'), 'client_secret':os.getenv('CLIENT_SECRET')})  
        filters = {'pageSize': 1000, 'currentPage': currentPage}
        request = requests.get(consulta, headers=headers, data=json_data, params=filters)
        dados = json.loads(request.text)
        if dados['data']:
            currentPage += 1
            for dado in dados['data']:
                consulta = Fornecedor.objects.filter(cod_fornecedor=dado['fornecedorKey'])
                if not consulta:
                    novos += 1
                    fornecedor = Fornecedor(
                        cod_fornecedor = dado['fornecedorKey'],
                        razao_fornecedor = dado['nomeRazao'],
                        cgc_fornecedor = dado['cpfCnpj'],
                        dt_cadastro = dado.get('dataCadastro', '-'),
                        status_fornecedor = dado['ativa']
                    )
                    fornecedor.save()
                else:
                    atualizados += 1
                    Fornecedor.objects.filter(cod_fornecedor=dado['fornecedorKey']).update(
                        razao_fornecedor = dado['nomeRazao'],
                        cgc_fornecedor = dado['cpfCnpj'],
                        dt_cadastro = dado.get('dataCadastro', '-'),
                        status_fornecedor = dado['ativa']
                    )
        else:
            flag = 1
            
    return 0