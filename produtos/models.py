from django.db import models
from django.contrib.auth.models import User

from controle.models import Loja


class Produto(models.Model):
    cod_produto = models.IntegerField(primary_key=True, verbose_name='Código do produto')
    desc_produto = models.CharField(max_length=500, verbose_name='Descrição do produto')
    cod_gtin_principal = models.CharField(max_length=50, verbose_name='Código de barras principal')
    cod_gtins_disponiveis = models.CharField(max_length=500, verbose_name='Código de barras disponíveis')
    dt_cadastro = models.CharField(verbose_name='Data de cadastro')
    dt_ult_alteracao = models.CharField(verbose_name='Data da última alteração')
    status_produto = models.CharField(max_length=50, verbose_name='Status do produto')
    desc_marca = models.CharField(null=True, blank=True, max_length=500, verbose_name='Descrição da marca do produto')
    foto_produto = models.FileField(null=True, blank=True)
    caixa = models.BooleanField(default=False, verbose_name='Indicação que o produto é caixa')


class Validade(models.Model):

    TIPO_LOTE_CHOICES = [('TF', 'TROCA FORNECEDOR'), ('SG', 'SEM GARANTIA')]

    id_produto = models.ForeignKey(Produto, on_delete=models.CASCADE, verbose_name='Código do produto')
    cod_loja = models.ForeignKey(Loja, on_delete=models.CASCADE, verbose_name='Código da loja')
    usuario_cadastro = models.ForeignKey(User, on_delete=models.CASCADE, related_name='Usuário de cadastro+')
    usuario_ultimo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='Usuário da última alteração+')
    data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data e hora de cadastro')
    data_ultima = models.DateTimeField(auto_now=True, verbose_name='Data e hora da última alteração')
    num_lote = models.CharField(max_length=50, verbose_name='Lote do produto')
    dt_validade = models.DateField(db_index=True, verbose_name='Data de validade')
    qt_lote = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Quantidade do item do lote')
    tipo_lote = models.CharField(max_length=100, choices=TIPO_LOTE_CHOICES, verbose_name='Tipo do lote do produto')
    obs_geral = models.TextField(max_length=500, verbose_name='Observações gerais')
    ativo = models.BooleanField(default=True, verbose_name='Status do lote')
    promocao_ativa = models.BooleanField(default=False, verbose_name='Promoção ativa')

    class Meta:
        # Cria um índice inteligente combinando o status, a loja e a data
        indexes = [
            models.Index(fields=['ativo', 'cod_loja', 'dt_validade']),
        ]


class Ruptura(models.Model):
    
    STATUS_CHOICES = [
        ('EM_ABERTO', 'Em Aberto'),
        ('AGUARDANDO_FORNECEDOR', 'Aguardando Fornecedor'),
        ('RESOLVIDO', 'Resolvido pelo Comprador'),
        ('FINALIZADO', 'Finalizado pela Loja'),
        ('PENDENTE', 'Pendente / Reaberto'),
    ]

    loja_id = models.ForeignKey(Loja, on_delete=models.CASCADE, verbose_name='Código da loja')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='rupturas', verbose_name="Produto")
    quantidade_necessaria = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Qtd. Necessária")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='EM_ABERTO', verbose_name="Status")
    
    observacao_loja = models.TextField(blank=True, null=True, verbose_name="Obs. da Loja")
    observacao_comprador = models.TextField(blank=True, null=True, verbose_name="Obs. do Comprador")
    
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='rupturas_criadas')
    atualizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='rupturas_atualizadas')
    
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Ruptura'
        verbose_name_plural = 'Rupturas'

    def __str__(self):
        return f"Ruptura #{self.id} - {self.produto.desc_produto} ({self.get_status_display()})"


class ArvoreMercadologica(models.Model):
    categoria_bluesoft = models.IntegerField(primary_key=True, verbose_name='Código-chave da categoria na BlueSoft')
    categoria_pai_bluesoft = models.IntegerField(null=True, verbose_name='Código-chave da categoria na BlueSoft')
    tipo_categoria = models.CharField(max_length=100, verbose_name='Tipo de categoria')
    nome_categoria = models.CharField(max_length=500, verbose_name='Nome da categoria')
