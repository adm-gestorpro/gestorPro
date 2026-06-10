from django.shortcuts import render

def erro_403_customizado(request, exception=None):
    # Você pode passar qualquer contexto que quiser para o HTML aqui
    contexto = {
        'usuario': request.user,
        'mensagem_extra': "Área restrita para a gerência."
    }
    # Renderiza o template 403.html passando o contexto, com o status do erro
    return render(request, '403.html', contexto, status=403)