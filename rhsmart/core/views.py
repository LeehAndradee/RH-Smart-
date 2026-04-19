from django.shortcuts import render
from .models import Funcionario, Cargo, Departamento


def funcionarios_view(request):
    funcionarios = Funcionario.objects.all()
    return render(request, 'core/funcionarios.html', {
        'funcionarios': funcionarios
    })


def cargos_view(request):
    cargos = Cargo.objects.all()
    return render(request, 'core/cargos.html', {
        'cargos': cargos
    })


def departamentos_view(request):
    departamentos = Departamento.objects.all()
    return render(request, 'core/departamentos.html', {
        'departamentos': departamentos
    })