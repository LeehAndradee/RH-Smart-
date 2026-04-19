from django.shortcuts import render, redirect, get_object_or_404
from .models import Funcionario, Cargo, Departamento, FolhaPagamento
from django.db.models import Sum
from datetime import datetime


# =========================
# DASHBOARD
# =========================
def dashboard_view(request):
    total_funcionarios = Funcionario.objects.count()
    folhas_fechadas = FolhaPagamento.objects.filter(fechada=True).count()
    folhas_pendentes = FolhaPagamento.objects.filter(fechada=False).count()

    total_pago = FolhaPagamento.objects.aggregate(
        total=Sum('salario_liquido')
    )['total'] or 0

    return render(request, 'core/dashboard.html', {
        'total_funcionarios': total_funcionarios,
        'folhas_fechadas': folhas_fechadas,
        'folhas_pendentes': folhas_pendentes,
        'total_pago': total_pago
    })


# =========================
# FUNCIONÁRIOS
# =========================
def funcionarios_view(request):
    funcionarios = Funcionario.objects.all()
    return render(request, 'core/funcionarios.html', {'funcionarios': funcionarios})


def funcionario_create(request):
    if request.method == 'POST':
        Funcionario.objects.create(
            nome=request.POST.get('nome'),
            cpf=request.POST.get('cpf'),
            data_nascimento=request.POST.get('data_nascimento') or None,
            dependentes=int(request.POST.get('dependentes') or 0),
            escolaridade=request.POST.get('escolaridade'),
            estado_civil=request.POST.get('estado_civil'),
            salario_base=request.POST.get('salario'),
            data_admissao=request.POST.get('admissao'),
            cargo_id=request.POST.get('cargo')
        )
        return redirect('/funcionarios/')

    cargos = Cargo.objects.all()
    return render(request, 'core/form_funcionario.html', {'cargos': cargos})


def funcionario_update(request, id):
    funcionario = get_object_or_404(Funcionario, id=id)

    if request.method == 'POST':
        funcionario.nome = request.POST.get('nome')
        funcionario.cpf = request.POST.get('cpf')
        funcionario.data_nascimento = request.POST.get('data_nascimento') or None
        funcionario.dependentes = int(request.POST.get('dependentes') or 0)
        funcionario.escolaridade = request.POST.get('escolaridade')
        funcionario.estado_civil = request.POST.get('estado_civil')
        funcionario.salario_base = request.POST.get('salario')
        funcionario.data_admissao = request.POST.get('admissao')
        funcionario.cargo_id = request.POST.get('cargo')

        funcionario.save()
        return redirect('/funcionarios/')

    cargos = Cargo.objects.all()
    return render(request, 'core/form_funcionario.html', {
        'funcionario': funcionario,
        'cargos': cargos
    })


def funcionario_delete(request, id):
    funcionario = get_object_or_404(Funcionario, id=id)
    funcionario.delete()
    return redirect('/funcionarios/')


# =========================
# CARGOS
# =========================
def cargos_view(request):
    cargos = Cargo.objects.select_related('departamento').all()
    return render(request, 'core/cargos.html', {'cargos': cargos})


def cargo_create(request):
    if request.method == 'POST':
        Cargo.objects.create(
            nome=request.POST.get('nome'),
            nivel=request.POST.get('nivel'),
            carga_horaria=int(request.POST.get('carga') or 40),
            departamento_id=request.POST.get('departamento')
        )
        return redirect('/cargos/')

    departamentos = Departamento.objects.all()
    return render(request, 'core/form_cargo.html', {'departamentos': departamentos})


def cargo_update(request, id):
    cargo = get_object_or_404(Cargo, id=id)

    if request.method == 'POST':
        cargo.nome = request.POST.get('nome')
        cargo.nivel = request.POST.get('nivel')
        cargo.carga_horaria = int(request.POST.get('carga') or 40)
        cargo.departamento_id = request.POST.get('departamento')
        cargo.save()

        return redirect('/cargos/')

    departamentos = Departamento.objects.all()
    return render(request, 'core/form_cargo.html', {
        'cargo': cargo,
        'departamentos': departamentos
    })


def cargo_delete(request, id):
    cargo = get_object_or_404(Cargo, id=id)
    cargo.delete()
    return redirect('/cargos/')


# =========================
# DEPARTAMENTOS
# =========================
def departamentos_view(request):
    departamentos = Departamento.objects.all()
    return render(request, 'core/departamentos.html', {'departamentos': departamentos})


def departamento_create(request):
    if request.method == 'POST':
        Departamento.objects.create(
            nome=request.POST.get('nome'),
            descricao=request.POST.get('descricao')
        )
        return redirect('/departamentos/')

    return render(request, 'core/form_departamento.html')


def departamento_update(request, id):
    departamento = get_object_or_404(Departamento, id=id)

    if request.method == 'POST':
        departamento.nome = request.POST.get('nome')
        departamento.descricao = request.POST.get('descricao')
        departamento.save()

        return redirect('/departamentos/')

    return render(request, 'core/form_departamento.html', {
        'departamento': departamento
    })


def departamento_delete(request, id):
    departamento = get_object_or_404(Departamento, id=id)
    departamento.delete()
    return redirect('/departamentos/')