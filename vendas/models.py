from django.db import models

from controle.models import Loja
from produtos.models import Produto

class Vendedor(models.Model):
    #Identificação do vendedor
    cod_vendedor = models.IntegerField(primary_key=True, verbose_name='Código do vendedor')
    id_operador = models.IntegerField(verbose_name='Código de integração do vendedor')
    nome_vendedor = models.CharField(max_length=500, verbose_name='Nome do vendedor')

    def __str__(self):
        return f"{self.cod_vendedor} - {self.nome_vendedor}"
    
    class Meta:
        ordering = ['nome_vendedor']
        verbose_name = 'Vendedor'
        verbose_name_plural = 'Vendedores'


class Faturamento(models.Model):
    #Identificação por chaves estrangeiras
    id_produto = models.ForeignKey(Produto, on_delete=models.CASCADE, verbose_name='Código do item vendido')
    cod_loja = models.ForeignKey(Loja, on_delete=models.CASCADE, verbose_name='Código da loja de venda')

    #Identificação do documento fiscal
    emissao_doc = models.DateTimeField(verbose_name='Data de emissão do documento gerado')
    numero_doc = models.IntegerField(verbose_name='Número do documento fiscal gerado')
    pedido_doc = models.IntegerField(verbose_name='Número pedido gerado')
    modelo_doc = models.IntegerField(verbose_name='Modelo do documento fiscal gerado')
    chave_doc = models.CharField(max_length=50, verbose_name='Chave de acesso do documento fiscal gerado')
    serie_doc = models.IntegerField(verbose_name='Série do documento fiscal gerado')
    equipamento_doc = models.IntegerField(verbose_name='Equipamento onde o documento fiscal foi gerado')

    #Identificação da venda
    operador = models.IntegerField(default=0, blank=True, null=True, verbose_name='Operador de venda')
    vendedor = models.ForeignKey(Vendedor, on_delete=models.CASCADE, verbose_name='Código do vendedor')
    ean_fat = models.CharField(max_length=50, verbose_name='Código de barras da venda')
    qt_fat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Quantidade faturada do item')
    valor_venda = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Valor faturado do produto')
    status_doc = models.BooleanField(default=True, verbose_name='Status do documento fiscal gerado')
    obs_geral = models.TextField(max_length=500, verbose_name='Observações gerais do pedido')
