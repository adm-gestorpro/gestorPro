from django.shortcuts import render
from django.core.paginator import Paginator

from fornecedores.models import Fornecedor

def listar_fornecedores(request):
    fornecedores_list = Fornecedor.objects.all().order_by('cod_fornecedor')

    per_page = request.GET.get('per_page', 10)
    paginator = Paginator(fornecedores_list, per_page)

    page_number = request.GET.get('page')
    fornecedores = paginator.get_page(page_number)

    context = {'fornecedores': fornecedores,'per_page': int(per_page)}

    return render(request, 'listar_fornecedores.html', context)