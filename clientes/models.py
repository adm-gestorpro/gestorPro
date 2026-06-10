from django.db import models

class Cliente(models.Model):
    cod_cliente = models.IntegerField(primary_key=True, verbose_name="Código do cliente")
    nome_cliente = models.CharField(verbose_name="Nome do cliente")
    cgc_cliente = models.CharField(unique=True, verbose_name="CPF/CNPJ do cliente")
    contatos = models.JSONField(verbose_name='Contatos do cliente')
    enderecos = models.JSONField(verbose_name='Endereços do cliente')
    tipo_cliente = models.CharField(max_length=10, verbose_name='Tipo do cliente')
    dt_cadastro = models.CharField(blank=True, max_length=30, verbose_name='Data de cadastro do cliente')
    dt_ult_alteracao= models.CharField(max_length=30, verbose_name='Data da última alteração de cadastro do cliente')
    status = models.CharField(max_length=30, verbose_name='Status do cliente')
