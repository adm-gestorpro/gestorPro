from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User


class Rede(models.Model):
    cod_rede = models.IntegerField(primary_key=True, verbose_name='Código da rede')
    desc_rede = models.CharField(max_length=200, verbose_name='Descrição da rede')
    lojas_rede = models.CharField(max_length=1000, verbose_name='Lojas cadastradas da rede')

    def __str__(self):
        return f'{self.cod_rede} - {self.desc_rede}'

class Loja(models.Model):
    id_rede = models.ForeignKey(Rede, on_delete=models.CASCADE, verbose_name='Código da rede')
    cod_loja = models.IntegerField(primary_key=True, verbose_name='Código da loja')
    cgc_loja = models.CharField(max_length=20, verbose_name='CPF/CNPJ da loja')
    razao_social = models.CharField(max_length=500, verbose_name='Razão social da loja')
    nome_fantasia = models.CharField(max_length=500, verbose_name='Nome fantasia da loja')
    insc_estadual = models.CharField(max_length=50, verbose_name='Inscrição estadual da loja')
    contatos = models.JSONField(verbose_name='Contatos da loja')
    enderecos = models.JSONField(verbose_name='Endereços da loja')
    loja_ativa = models.BooleanField(verbose_name='Loja ativa')

    def __str__(self):
        return f'{self.nome_fantasia}'

class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    lojas = models.ManyToManyField(Loja, blank=True, related_name="perfis_lojas")
    redes = models.ManyToManyField(Rede, blank=True, related_name="perfis_redes")
    vendedor = models.ManyToManyField('vendas.Vendedor', blank=True, related_name="perfis_vendedores")
    token = models.CharField(max_length=255, blank=True, null=True)
    foto = models.ImageField(upload_to='perfis/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name}"

    def get_lojas_acessiveis(self):
        """
        Retorna um QuerySet com todas as lojas que este usuário pode acessar.
        """
        # 1. Busca todas as lojas vinculadas diretamente ao perfil
        lojas_diretas = self.lojas.all().order_by('cod_loja')
        
        # 2. Busca todas as lojas vinculadas às redes que o usuário tem permissão
        # Como Loja tem id_rede (ForeignKey), usamos a relação reversa
        lojas_por_rede = Loja.objects.order_by('cod_loja').filter(id_rede__in=self.redes.all())
        
        # 3. Une os dois resultados e remove duplicatas
        return (lojas_diretas | lojas_por_rede).distinct()


@receiver(post_save, sender=User)
def gerenciar_perfil_usuario(sender, instance, created, **kwargs):
    PerfilUsuario.objects.get_or_create(user=instance)