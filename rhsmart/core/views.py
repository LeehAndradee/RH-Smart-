from django.http import JsonResponse
from .models import Funcionario

def calcular_folha(request):
    funcionario_id = request.GET.get('funcionario')

    if not funcionario_id:
        return JsonResponse({'error': 'Funcionário não informado'})

    try:
        funcionario = Funcionario.objects.get(id=funcionario_id)

        return JsonResponse({
            'salario_base': float(funcionario.salario_base)
        })

    except Funcionario.DoesNotExist:
        return JsonResponse({'error': 'Funcionário não encontrado'})