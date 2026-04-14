from django.shortcuts import render, redirect
from .models import FolhaPagamento, Funcionario

def criar_folha(request):
    funcionarios = Funcionario.objects.all()

    if request.method == 'POST':
        tipo = request.POST.get('tipo')

        folha = FolhaPagamento.objects.create(
            funcionario_id=request.POST.get('funcionario'),
            mes=request.POST.get('mes'),
            ano=request.POST.get('ano'),
            tipo=tipo
        )

        folha.save()

        return redirect('criar_folha')

    return render(request, 'folha/criar_folha.html', {
        'funcionarios': funcionarios
    })