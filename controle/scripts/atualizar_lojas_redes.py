import requests, json, os

from dotenv import load_dotenv
from controle.models import Rede, Loja

def atualiza_redes():

    consulta = f'/redes'
    headers = {'Content-Type':'application/x-www-form-urlencoded', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': os.getenv('TOKEN_BLUESOFT')}
    json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':os.getenv('CLIENT_ID'), 'client_secret':os.getenv('CLIENT_SECRET')})
    request = requests.get(os.getenv('URL_BASE_API')+consulta, headers=headers, data=json_data)
    dados = json.loads(request.text)

    for dado in dados:
        if dado['redeKey'] != 1:
            consulta = Rede.objects.filter(cod_rede=dado['redeKey'])
            if not consulta:
                redes = Rede(
                    cod_rede = dado['redeKey'],
                    desc_rede = dado['descricao'],
                    lojas_rede = dado['lojasKeys']
                )
                redes.save()


def atualiza_lojas():
    redes = Rede.objects.all()
    for rede in redes:
        consulta = f'/lojas'
        headers = {'Content-Type':'application/x-www-form-urlencoded', 'Cookie':'OAUTH=OAUTH_240', 'X-Customtoken': os.getenv('TOKEN_BLUESOFT')}
        filters = {'redeKey': rede.cod_rede}
        json_data = json.dumps({'grant_type':'client_credentials', 'scope':'switch.read', 'client_id':os.getenv('CLIENT_ID'), 'client_secret':os.getenv('CLIENT_SECRET')})
        request = requests.get(os.getenv('URL_BASE_API')+consulta, headers=headers, data=json_data, params=filters)
        dados = json.loads(request.text)

        for dado in dados['lojas']:
            consulta = Loja.objects.filter(cod_loja=dado['lojaKey'])
            if not consulta:
                lojas = Loja(
                    id_rede = rede,
                    cod_loja = dado['lojaKey'],
                    cgc_loja = dado['cpfCnpj'],
                    razao_social = dado['nomeRazao'],
                    nome_fantasia = dado['nomeFantasia'],
                    insc_estadual = dado['inscricaoEstadual'],
                    contatos = dado['contatos'],
                    enderecos = dado['enderecos'],
                    loja_ativa = dado['ativa']
                )
                lojas.save()
