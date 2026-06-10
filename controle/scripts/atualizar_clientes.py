import requests, json, os

from dotenv import load_dotenv
from clientes.models import Cliente


def atualiza_clientes():
    currentPage = 0
    consulta = f'{os.getenv('URL_BASE_API')}/clientes'
    headers = {'Content-Type':'application/x-www-form-urlencoded', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': os.getenv('TOKEN_BLUESOFT')}
    json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':os.getenv('CLIENT_ID'), 'client_secret':os.getenv('CLIENT_SECRET')})  
    flag = 0
    while flag == 0:
        filters = {'status': 'TODOS', 'pageSize': 1000, 'currentPage': currentPage}
        request = requests.get(consulta, headers=headers, data=json_data, params=filters)
        dados = json.loads(request.text)
        if dados['data']:
            currentPage += 1
            for dado in dados['data']:
                clientes = Cliente.objects.filter(cod_cliente=dado['clienteKey'])
                if not clientes:
                    if dado.get('dataCadastro') is not None:
                        cliente = Cliente(
                            cod_cliente = dado['clienteKey'],
                            nome_cliente = dado['nomeRazao'],
                            cgc_cliente = dado['cpfCnpj'],
                            contatos = dado['contatos'],
                            enderecos = dado['enderecos'],
                            tipo_cliente = dado['tipo'],
                            dt_cadastro = dado['dataCadastro'],
                            dt_ult_alteracao = dado['ultimaAlteracao'],
                            status = dado['clienteStatus']
                        )
                        cliente.save()
                    else:
                        cliente = Cliente(
                            cod_cliente = dado['clienteKey'],
                            nome_cliente = dado['nomeRazao'],
                            cgc_cliente = dado['cpfCnpj'],
                            contatos = dado['contatos'],
                            enderecos = dado['enderecos'],
                            tipo_cliente = dado['tipo'],
                            dt_cadastro = '',
                            dt_ult_alteracao = dado['ultimaAlteracao'],
                            status = dado['clienteStatus']
                        )
                        cliente.save()
        else:
            flag = 1

