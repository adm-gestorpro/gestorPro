from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Notificacao(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificacoes')
    mensagem = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True, null=True) # Link para o chamado ou relatório
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criada_em']

    def __str__(self):
        return f"Notificação para {self.usuario.first_name}: {self.mensagem}"