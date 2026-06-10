from django.db import models


class Fornecedor(models.Model):
    cod_fornecedor = models.IntegerField(primary_key=True, verbose_name='Código do fornecedor')
    razao_fornecedor = models.CharField(max_length=500, verbose_name='Razão social do fornecedor')
    cgc_fornecedor = models.CharField(max_length=50, verbose_name='CGC do fornecedor')
    dt_cadastro = models.CharField(verbose_name='Data de cadastro')
    status_fornecedor = models.CharField(max_length=50, verbose_name='Status do fornecedor')
