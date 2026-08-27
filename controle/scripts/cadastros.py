'''
    Esse módulo serve para buscar dados na API BlueSoft para atualização e
    cadastrar dados dos produtos e demais recursos.
'''

import os
import json
import requests

from produtos.models import ArvoreMercadologica

headers = {
    'Content-Type':'application/x-www-form-urlencoded', 
    'Cookie':'OAUTH=OAUTH_240', 
    'X-Customtoken': os.getenv('TOKEN_BLUESOFT')
    }

json_data = json.dumps({
    'grant_type':'client_credentials', 
    'scope':'switch.read', 
    'client_id':os.getenv('CLIENT_ID'), 
    'client_secret':os.getenv('CLIENT_SECRET')
    })

TIMEOUT_REQUEST = 5


def arvore_mercadologica():
    '''
        Método para fazer a consulta da árvore mercadológica dos produtos
        e gravar dados atualizados.
    '''

    categorias_bluesoft = ['DEPARTAMENTO','SECAO','GRUPO','SUBGRUPO']

    for categoria in categorias_bluesoft:
        current_page = 0
        consulta_api = f'{os.getenv('URL_BASE_API')}/comercial/arvoremercadologica'
        filters = {
            'pageSize': 1000, 
            'currentPage': current_page,
            'tipo': categoria
            }
        request = requests.get(
            consulta_api,
            headers=headers,
            data=json_data,
            params=filters,
            timeout=TIMEOUT_REQUEST
            )
        dados = json.loads(request.text)
        if dados:
            for dado in dados:
                categoria = ArvoreMercadologica.objects.filter(
                    categoria_bluesoft=dado['categoriaKey']
                    )
                if categoria:
                    categoria.categoria_pai_bluesoft=dado.get('categoriaPaiKey',None)
                    categoria.tipo_categoria=dado['tipo']
                    categoria.nome_categoria=dado['nome']
                    categoria.save()
                else:
                    cadastro = ArvoreMercadologica(
                        categoria_bluesoft=dado['categoriaKey'],
                        categoria_pai_bluesoft=dado.get('categoriaPaiKey',None),
                        tipo_categoria=dado['tipo'],
                        nome_categoria=dado['nome']
                        )
                    cadastro.save()
